import sys
import os
import torch
import logging

logger = logging.getLogger(__name__)

# Add trained-agent to path so cage4.py can resolve its internal imports
TRAINED_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "trained-agent")
)

# Constants matching the trained agent architecture
MAX_SERVERS = 6
MAX_USERS = 10
NUM_ROUTERS = 9

# Map our containers to CybORG-equivalent roles
# (role_type, index_within_role)
# Handles both short names and full clab-fyp-defense-network- prefixed names
CONTAINER_ROLES = {
    "web-server": ("server", 0),
    "clab-fyp-defense-network-web-server": ("server", 0),
    "database": ("server", 1),
    "clab-fyp-defense-network-database": ("server", 1),
    "public-web": ("server", 2),
    "clab-fyp-defense-network-public-web": ("server", 2),
    "admin-ws": ("user", 0),
    "clab-fyp-defense-network-admin-ws": ("user", 0),
    "attacker": None,
    "clab-fyp-defense-network-attacker": None,  # external threat — not a defense target
}

# CAGE4 node action types → bridge actions
# 0=Analyse, 1=Remove, 2=Restore, 3=DeployDecoy
ACTION_TYPE_MAP = {
    0: "Analyse",
    1: "Remove",
    2: "Restore",
    3: "DeployDecoy",
}

# Map edge action router indices (0-7) to container-interface pairs
# CybORG has subnet routers; we map to the actual interfaces in our topology
ROUTER_TO_INTERFACE = {
    0: ("web-server", "eth1"),    # Admin zone boundary
    1: ("web-server", "eth2"),    # Operational zone (database) boundary
    2: ("web-server", "eth3"),    # Public zone boundary
    3: ("public-web", "eth1"),    # Public-internal interface
    4: ("public-web", "eth2"),    # Attacker-facing interface
    5: ("database", "eth1"),      # Database interface
    6: ("admin-ws", "eth1"),      # Admin workstation interface
    7: ("web-server", "eth1"),    # Fallback
}


def _load_agent(weights_path):
    """Load trained GNN-PPO agent from checkpoint file."""
    if TRAINED_AGENT_DIR not in sys.path:
        sys.path.insert(0, TRAINED_AGENT_DIR)

    from models.cage4 import InductiveGraphPPOAgent

    data = torch.load(weights_path, map_location="cpu", weights_only=False)
    args, kwargs = data["agent"]

    agent = InductiveGraphPPOAgent(*args, **kwargs)
    agent.actor.load_state_dict(data["actor"])
    agent.critic.load_state_dict(data["critic"])
    agent.eval()
    agent.set_deterministic(False)  # Stochastic: sample from policy distribution for action variety

    return agent


class AgentAdapter:
    """Bridges the trained GNN-PPO agent with our containerlab network.

    Handles:
    - Feature padding (our 200-dim → agent's expected in_dim)
    - Adding dummy router nodes (required by agent architecture)
    - Structuring the state tuple (servers, users, edges, etc.)
    - Decoding action indices to (action_type, target_container)
    """

    def __init__(self, weights_path):
        self.agent = _load_agent(weights_path)
        self.in_dim = self.agent.actor.conv1.in_channels
        logger.info(f"Loaded agent (in_dim={self.in_dim})")

        self._server_names = []
        self._user_names = []

    def get_action(self, graph, container_names):
        """
        Run the trained agent on an observation graph.

        Args:
            graph: PyG Data object from ObservationGraphBuilder
            container_names: list of container names matching SystemNode order

        Returns:
            dict with 'type', 'target', 'raw_index'
        """
        state = self._build_state(graph, container_names)
        obs = (state, False)  # (state_tuple, is_blocked=False)

        action_idx = self.agent.get_action(obs)
        decoded = self._decode_action(action_idx, container_names)

        logger.info(f"Agent action index {action_idx} -> {decoded['type']} on {decoded['target']}")
        decoded["raw_index"] = action_idx
        return decoded

    def _build_state(self, graph, container_names):
        """Convert our PyG graph into the state tuple the agent expects."""
        num_nodes = graph.x.shape[0]
        feat_dim = graph.x.shape[1]

        # 1. Feature padding & Router addition
        if hasattr(graph, 'num_real'):
            # Case A: Graph is already padded (v4 builder)
            # Ensure we truncate to expected input dim (200 -> 192)
            x_raw = graph.x
            x = x_raw[:, : self.in_dim]
            num_real = graph.num_real
            
            # Router indices are immediately after real nodes
            local_router = num_real
            neighbors = list(range(num_real + 1, num_real + 9))  # 8 neighbors
            
            logger.info(f"   Using pre-padded graph: {num_real} real nodes, routers at {local_router}-{neighbors[-1]}")
        else:
            # Case B: Raw graph (v1/v2/v3 builder), need to add routers
            if feat_dim < self.in_dim:
                padding = torch.zeros(num_nodes, self.in_dim - feat_dim)
                x = torch.cat([graph.x, padding], dim=1)
            else:
                x = graph.x[:, : self.in_dim]

            # Append 9 dummy router nodes
            router_features = torch.zeros(NUM_ROUTERS, self.in_dim)
            x = torch.cat([x, router_features], dim=0)
            
            local_router = num_nodes
            neighbors = list(range(num_nodes + 1, num_nodes + NUM_ROUTERS))

        # 3. Edge index
        ei = graph.edge_index

        # DEBUG: Log feature statistics
        logger.info(f"   🔍 Feature shape: {x.shape}")
        logger.info(f"   🔍 Checking compromise flags in first 5 nodes:")
        for i in range(min(5, x.shape[0])):
            nonzero = (x[i] != 0).sum().item()
            compromised = x[i][187].item() if x.shape[1] > 187 else -999
            scanned = x[i][188].item() if x.shape[1] > 188 else -999
            logger.info(f"      Node {i}: {nonzero}/{x.shape[1]} non-zero | pos[187]={compromised:.2f} (compromised?) | pos[188]={scanned:.2f} (scanned?)")
            if i < 2:  # Show all non-zero positions for first 2 nodes
                nonzero_indices = x[i].nonzero().squeeze().tolist()
                logger.info(f"         Non-zero indices: {nonzero_indices}")

        # 4. Global state vector — mission phase (one-hot, 3 phases)
        # Force Phase 1 (Active Attack) to encourage Restore
        global_vec = torch.tensor([[0.0, 1.0, 0.0]])

        # 5. Classify our containers as servers or users
        # ... (classification code remains same) ...
        server_indices = []
        user_indices = []
        self._server_names = []
        self._user_names = []
        
        for i, name in enumerate(container_names):
            role = CONTAINER_ROLES.get(name)
            if role is None: continue
            if role[0] == "server":
                server_indices.append(i)
                self._server_names.append(name)
            elif role[0] == "user":
                user_indices.append(i)
                self._user_names.append(name)

        servers = torch.tensor(server_indices, dtype=torch.long)
        n_servers = torch.tensor([len(server_indices)], dtype=torch.long)
        users = torch.tensor(user_indices, dtype=torch.long)
        n_users = torch.tensor([len(user_indices)], dtype=torch.long)

        # 6. Action edges
        action_edges = torch.tensor(
            [[local_router] * 8, neighbors],
            dtype=torch.long,
        )

        multi_subnet = False

        return (
            x,
            ei,
            global_vec,
            servers,
            n_servers,
            users,
            n_users,
            action_edges,
            multi_subnet,
        )

    def _decode_action(self, action_idx, container_names):
        """Map agent's action index (0-80) to a decision dict."""
        if action_idx is None:
            return {"type": "Monitor", "target": container_names[0]}

        # Node actions: indices 0-63
        if action_idx < 64:
            action_type_idx = action_idx // 16  # 0-3
            host_idx = action_idx % 16

            bridge_action = ACTION_TYPE_MAP.get(action_type_idx, "Monitor")

            if host_idx < MAX_SERVERS:
                if host_idx < len(self._server_names):
                    target = self._server_names[host_idx]
                else:
                    target = self._server_names[0] if self._server_names else container_names[0]
            else:
                user_idx = host_idx - MAX_SERVERS
                if user_idx < len(self._user_names):
                    target = self._user_names[user_idx]
                else:
                    target = self._user_names[0] if self._user_names else container_names[0]

            return {"type": bridge_action, "target": target}

        # Edge actions: indices 64-79 (AllowTrafficZone / BlockTrafficZone)
        if action_idx < 80:
            edge_idx = action_idx - 64  # 0-15
            action_type_idx = edge_idx // 8  # 0=Allow, 1=Block
            router_idx = edge_idx % 8  # 0-7

            action_type = "AllowTrafficZone" if action_type_idx == 0 else "BlockTrafficZone"
            container, interface = ROUTER_TO_INTERFACE.get(
                router_idx, ("web-server", "eth1")
            )

            return {
                "type": action_type,
                "target": container,
                "interface": interface,
            }

        # Global action: index 80 (sleep/monitor)
        return {"type": "Monitor", "target": container_names[0]}