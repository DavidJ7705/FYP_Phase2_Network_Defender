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

# Map CAGE4 containers to CybORG-equivalent roles (MINIMAL TOPOLOGY)
# (role_type, index_within_role)
# Total: 6 servers + 10 users = 16 hosts (fits MAX_SERVERS=6, MAX_USERS=10)
CONTAINER_ROLES = {
    # Restricted Zone A (2 servers + 1 user)
    "restricted-zone-a-server-0": ("server", 0),
    "restricted-zone-a-server-1": ("server", 1),
    "restricted-zone-a-user-0": ("user", 0),

    # Operational Zone A (1 server + 1 user)
    "operational-zone-a-server-0": ("server", 2),
    "operational-zone-a-user-0": ("user", 1),

    # Restricted Zone B (1 server + 1 user)
    "restricted-zone-b-server-0": ("server", 3),
    "restricted-zone-b-user-0": ("user", 2),

    # Operational Zone B (1 server + 1 user)
    "operational-zone-b-server-0": ("server", 4),
    "operational-zone-b-user-0": ("user", 3),

    # Contractor Network (1 server + 2 users - red entry point)
    "contractor-network-server-0": ("server", 5),
    "contractor-network-user-0": ("user", 4),
    "contractor-network-user-1": ("user", 5),

    # Public Access Zone (1 user only)
    "public-access-zone-user-0": ("user", 6),

    # Admin Network (1 user only)
    "admin-network-user-0": ("user", 7),

    # Office Network (2 users only)
    "office-network-user-0": ("user", 8),
    "office-network-user-1": ("user", 9),

    # Exclude routers and internet host (not defense targets)
    "restricted-zone-a-router": None,
    "operational-zone-a-router": None,
    "restricted-zone-b-router": None,
    "operational-zone-b-router": None,
    "contractor-network-router": None,
    "public-access-zone-router": None,
    "admin-network-router": None,
    "office-network-router": None,
    "internet-router": None,
    "root-internet-host": None,
}

# CAGE4 node action types → bridge actions
# 0=Analyse, 1=Remove, 2=Restore, 3=DeployDecoy
ACTION_TYPE_MAP = {
    0: "Analyse",
    1: "Remove",
    2: "Restore",
    3: "DeployDecoy",
}

# Map edge action router indices (0-7) to CAGE4 router-interface pairs
# Agent's edge actions target these routers for traffic control
ROUTER_TO_INTERFACE = {
    0: ("restricted-zone-a-router", "eth2"),
    1: ("operational-zone-a-router", "eth2"),
    2: ("restricted-zone-b-router", "eth2"),
    3: ("operational-zone-b-router", "eth2"),
    4: ("contractor-network-router", "eth2"),
    5: ("public-access-zone-router", "eth2"),
    6: ("admin-network-router", "eth2"),
    7: ("office-network-router", "eth2"),
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
    agent.set_deterministic(False)  # Deterministic: always pick highest-probability action

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

        # Get action distribution to inspect probabilities
        distro = self.agent.actor(*state)
        probs = distro.probs[0]  # Get probabilities for all 80 actions

        # Show top 5 actions and their probabilities
        top_probs, top_indices = torch.topk(probs, k=5)
        logger.info("   [AGENT DEBUG] Top 5 action probabilities:")
        for i, (prob, idx) in enumerate(zip(top_probs.tolist(), top_indices.tolist())):
            decoded_action = self._decode_action(idx, container_names)
            logger.info(f"      {i+1}. P={prob:.3f} -> {decoded_action['type']} on {decoded_action['target']}")

        # DIAGNOSTIC: Show all Restore action probabilities (indices 32-47)
        logger.info("   [DIAGNOSTIC] All Restore action probabilities:")
        for idx in range(32, 48):  # Restore actions = action_type 2, indices 32-47
            prob = probs[idx].item()
            decoded = self._decode_action(idx, container_names)
            if prob > 0.01:  # Only show if > 1%
                logger.info(f"      Restore on {decoded['target']}: P={prob:.3f}")

        action_idx = self.agent.get_action(obs)
        decoded = self._decode_action(action_idx, container_names)

        logger.info(f"Agent action index {action_idx} -> {decoded['type']} on {decoded['target']}")
        decoded["raw_index"] = action_idx
        return decoded

    def _build_state(self, graph, container_names):
        """Convert our PyG graph into the state tuple the agent expects."""
        num_nodes = graph.x.shape[0]
        feat_dim = graph.x.shape[1]

        # 1. Feature padding & Router extraction
        if hasattr(graph, 'num_routers'):
            # CAGE4 router-mediated graph: routers are real nodes (last 9)
            x_raw = graph.x
            x = x_raw[:, : self.in_dim]  # Truncate to expected input dim (200 -> 192)

            # Routers are last num_routers nodes
            num_hosts = graph.num_servers + graph.num_users
            router_indices = list(range(num_hosts, num_hosts + graph.num_routers))

            assert len(router_indices) == 9, f"Expected 9 routers, got {len(router_indices)}"

            # Action edges: first router to next 8
            local_router = router_indices[0]
            neighbors = router_indices[1:9]

            logger.info(f"   CAGE4 graph: {graph.num_servers} servers, {graph.num_users} users, {graph.num_routers} routers")
            logger.info(f"   Routers at indices {router_indices[0]}-{router_indices[-1]}")
        elif hasattr(graph, 'num_real'):
            # Old padded graph (v4 builder) - fallback for compatibility
            x_raw = graph.x
            x = x_raw[:, : self.in_dim]
            num_real = graph.num_real

            local_router = num_real
            neighbors = list(range(num_real + 1, num_real + 9))

            logger.info(f"   Using pre-padded graph: {num_real} real nodes, routers at {local_router}-{neighbors[-1]}")
        else:
            # Raw graph - add dummy routers (very old builder)
            if feat_dim < self.in_dim:
                padding = torch.zeros(num_nodes, self.in_dim - feat_dim)
                x = torch.cat([graph.x, padding], dim=1)
            else:
                x = graph.x[:, : self.in_dim]

            router_features = torch.zeros(NUM_ROUTERS, self.in_dim)
            x = torch.cat([x, router_features], dim=0)

            local_router = num_nodes
            neighbors = list(range(num_nodes + 1, num_nodes + NUM_ROUTERS))

        # 3. Edge index
        ei = graph.edge_index

        # 4. Global state vector — mission phase (one-hot, 3 phases)
        # Phase 1 (Active Attack) - standard defensive posture
        global_vec = torch.tensor([[0.0, 1.0, 0.0]])

        # 5. Classify our containers as servers or users using GRAPH-ORDER indices.
        # The graph builder places servers first (0..n_s-1), users next (n_s..n_s+n_u-1).
        # We must use those positions — NOT the Docker container list positions — so that
        # x[server_indices[i]] actually contains the features for _server_names[i].
        server_indices = []
        user_indices = []
        self._server_names = []
        self._user_names = []

        server_graph_idx = 0
        user_graph_idx = graph.num_servers  # users start after all servers in the graph

        for name in container_names:
            role = CONTAINER_ROLES.get(name)
            if role is None:
                continue
            if role[0] == "server":
                server_indices.append(server_graph_idx)
                self._server_names.append(name)
                server_graph_idx += 1
            elif role[0] == "user":
                user_indices.append(user_graph_idx)
                self._user_names.append(name)
                user_graph_idx += 1

        servers = torch.tensor(server_indices, dtype=torch.long)
        n_servers = torch.tensor([len(server_indices)], dtype=torch.long)
        users = torch.tensor(user_indices, dtype=torch.long)
        n_users = torch.tensor([len(user_indices)], dtype=torch.long)

        logger.debug("   [INDEX MAP] Servers: " + ", ".join(
            f"{idx}={name}" for idx, name in zip(server_indices, self._server_names)))
        logger.debug("   [INDEX MAP] Users: " + ", ".join(
            f"{idx}={name}" for idx, name in zip(user_indices, self._user_names)))

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