import torch
from torch_geometric.data import Data
import numpy as np

# Topology links from fyp-topology.yaml
TOPOLOGY_LINKS = [
    ("admin-ws", "web-server"),
    ("web-server", "database"),
    ("web-server", "public-web"),
    ("public-web", "attacker"),
]

FEATURE_DIM = 200


class ObservationGraphBuilder:
    """Convert Containerlab network state to GNN observation format."""

    NODE_TYPES = {
        "SystemNode": 0,
        "ConnectionNode": 1,
        "FileNode": 2,
        "InternetNode": 3,
    }

    def build_graph(self, network_state):
        """
        Convert network state to PyTorch Geometric graph.

        Args:
            network_state: Dict from network_monitor.get_network_state()

        Returns:
            torch_geometric.data.Data with:
                - x: [num_nodes, FEATURE_DIM] node features
                - edge_index: [2, num_edges] connectivity
                - node_type: [num_nodes] type labels (0-3)
        """
        nodes = self._create_nodes(network_state)
        edges = self._create_edges(network_state, nodes)

        return Data(
            x=torch.tensor(nodes["features"], dtype=torch.float32),
            edge_index=torch.tensor(edges, dtype=torch.long).t().contiguous(),
            node_type=torch.tensor(nodes["types"], dtype=torch.long),
        )

    def _create_nodes(self, state):
        """Map containers and their connections to graph nodes."""
        node_features = []
        node_types = []
        node_map = {}
        conn_node_map = {}  # Maps (container_name, port) -> node_idx
        node_idx = 0

        # SystemNodes — one per container
        for container in state["containers"]:
            features = self._encode_system_node(container, state)
            node_features.append(features)
            node_types.append(self.NODE_TYPES["SystemNode"])
            node_map[container["name"]] = node_idx
            node_idx += 1

        # ConnectionNodes — one per open port
        for container_name, ports in state["connections"].items():
            if isinstance(ports, list):
                for port in ports:
                    features = self._encode_connection_node(port, container_name)
                    node_features.append(features)
                    node_types.append(self.NODE_TYPES["ConnectionNode"])
                    conn_node_map[(container_name, port)] = node_idx
                    node_idx += 1

        return {
            "features": node_features,
            "types": node_types,
            "node_map": node_map,
            "conn_node_map": conn_node_map,
        }

    def _encode_system_node(self, container, state):
        """Encode container as a FEATURE_DIM-dimensional feature vector."""
        features = [0.0] * FEATURE_DIM

        # Basic presence/status
        features[0] = 1.0  # node exists
        features[1] = 1.0 if container["status"] == "running" else 0.0

        # Process count (normalized)
        processes = state["processes"].get(container["name"], [])
        if isinstance(processes, list):
            features[2] = min(len(processes) / 50.0, 1.0)

        # Open port count (normalized)
        ports = state["connections"].get(container["name"], [])
        if isinstance(ports, list):
            features[3] = min(len(ports) / 20.0, 1.0)

        # Role flags based on image
        image = container.get("image", "")
        features[4] = 1.0 if "nginx" in image else 0.0       # web server
        features[5] = 1.0 if "postgres" in image else 0.0     # database
        features[6] = 1.0 if "kali" in image or "attacker" in image else 0.0
        features[7] = 1.0 if "alpine" in image and "nginx" not in image and "postgres" not in image else 0.0  # workstation

        # IP address encoding (last octet, normalized)
        ip = container.get("ip", "0.0.0.0")
        octets = ip.split(".")
        if len(octets) == 4:
            features[8] = int(octets[2]) / 255.0   # subnet
            features[9] = int(octets[3]) / 255.0   # host

        return features

    def _encode_connection_node(self, port, container_name):
        """Encode network connection as a FEATURE_DIM-dimensional feature vector."""
        features = [0.0] * FEATURE_DIM

        features[0] = 1.0  # connection exists

        # Port number (normalized)
        try:
            port_num = int(port)
            features[1] = port_num / 65535.0
        except (ValueError, TypeError):
            features[1] = 0.0

        # Well-known port flags
        features[2] = 1.0 if port == "22" else 0.0     # SSH
        features[3] = 1.0 if port == "80" else 0.0     # HTTP
        features[4] = 1.0 if port == "443" else 0.0    # HTTPS
        features[5] = 1.0 if port == "3306" else 0.0   # MySQL
        features[6] = 1.0 if port == "5432" else 0.0   # PostgreSQL
        features[7] = 1.0 if port == "8080" else 0.0   # HTTP alt

        # Ephemeral port flag (ports > 32768 are typically ephemeral)
        try:
            features[8] = 1.0 if int(port) > 32768 else 0.0
        except (ValueError, TypeError):
            pass

        return features

    def _create_edges(self, state, nodes):
        """
        Create edges based on actual topology + container-to-port links.

        Edge types:
        - SystemNode <-> SystemNode: physical network links from topology
        - SystemNode <-> ConnectionNode: container has a listening port
        """
        edge_list = []
        node_map = nodes["node_map"]
        conn_node_map = nodes["conn_node_map"]

        # Topology edges (bidirectional)
        for src, dst in TOPOLOGY_LINKS:
            if src in node_map and dst in node_map:
                edge_list.append([node_map[src], node_map[dst]])
                edge_list.append([node_map[dst], node_map[src]])

        # Container -> port edges (bidirectional)
        for (container_name, port), conn_idx in conn_node_map.items():
            if container_name in node_map:
                sys_idx = node_map[container_name]
                edge_list.append([sys_idx, conn_idx])
                edge_list.append([conn_idx, sys_idx])

        if not edge_list:
            edge_list = [[0, 0]]  # PyG needs at least one edge

        return edge_list
