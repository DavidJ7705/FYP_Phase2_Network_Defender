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

# CAGE4 node action types → our available bridge actions
# 0=Analyse, 1=Remove, 2=Restore, 3=DeployDecoy
ACTION_TYPE_MAP = {
    0: "Analyse",
    1: "Analyse",   # Remove → Analyse (closest equivalent)
    2: "Restore",
    3: "Monitor",   # DeployDecoy → Monitor (not available)
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
    agent.set_deterministic(True)

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
        action_type, target = self._decode_action(action_idx, container_names)

        logger.info(f"Agent action index {action_idx} -> {action_type} on {target}")
        return {"type": action_type, "target": target, "raw_index": action_idx}

    def _build_state(self, graph, container_names):
        """Convert our PyG graph into the state tuple the agent expects."""
        num_nodes = graph.x.shape[0]
        feat_dim = graph.x.shape[1]

        # 1. Pad node features to match agent's in_dim
        if feat_dim < self.in_dim:
            padding = torch.zeros(num_nodes, self.in_dim - feat_dim)
            x = torch.cat([graph.x, padding], dim=1)
        else:
            x = graph.x[:, : self.in_dim]

        # 2. Append 9 dummy router nodes (agent architecture requires them)
        router_features = torch.zeros(NUM_ROUTERS, self.in_dim)
        x = torch.cat([x, router_features], dim=0)

        # 3. Edge index — keep existing edges, routers are isolated
        #    GCNConv adds self-loops so isolated nodes still get processed
        ei = graph.edge_index

        # 4. Global state vector — mission phase (one-hot, 3 phases)
        global_vec = torch.tensor([[1.0, 0.0, 0.0]])

        # 5. Classify our containers as servers or users
        server_indices = []
        user_indices = []
        self._server_names = []
        self._user_names = []

        for i, name in enumerate(container_names):
            role = CONTAINER_ROLES.get(name)
            if role is None:
                continue
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

        # 6. Action edges — local router connects to 8 neighbor routers
        local_router = num_nodes  # first dummy router
        neighbors = list(range(num_nodes + 1, num_nodes + NUM_ROUTERS))
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
        """Map agent's action index (0-80) to (action_type, target_container)."""
        if action_idx is None:
            return "Monitor", container_names[0]

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

            return bridge_action, target

        # Edge actions: indices 64-79 (firewall — not available)
        if action_idx < 80:
            return "Monitor", container_names[0]

        # Global action: index 80 (sleep/monitor)
        return "Monitor", container_names[0]