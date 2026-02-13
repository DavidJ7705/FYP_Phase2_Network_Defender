import torch
from torch_geometric.data import Data
import numpy as np


class ObservationGraphBuilder:
    """
    Convert Containerlab network state to GNN observation format
    matching the trained agent's EXACT 192-dim feature encoding
    """

    # Must match the trained agent's node type encoding
    NODE_TYPES = {
        'SystemNode': 0,
        'ConnectionNode': 1,
        'FileNode': 2,
        'InternetNode': 3
    }

    # Feature dimensions matching trained agent
    # See trained-agent/wrapper/nodes.py and observation_graph.py
    SYSTEM_DIM = 170  # Architecture + OS + patches + crown_jewel/user/server/router flags
    CONNECTION_DIM = 40  # process_name + process_type + suspicious/decoy/default/ephemeral flags
    FILE_DIM = 60  # File metadata
    INTERNET_DIM = 0  # No features

    def build_graph(self, network_state):
        """
        Convert network state to PyTorch Geometric graph with features
        matching the trained agent's 192-dim encoding:
        
        [4 node_type_onehot | node_features | 9 subnet | 2 tabular | 3 message] = 192 total

        Args:
            network_state: Dict from network_monitor.get_network_state()

        Returns:
            torch_geometric.data.Data with:
                - x: [num_nodes, 192] node features 
                - edge_index: [2, num_edges] connectivity
                - node_type: [num_nodes] type labels (0-3)
        """
        nodes = self._create_nodes(network_state)
        edges = self._create_edges(network_state, nodes)

        return Data(
            x=torch.tensor(nodes['features'], dtype=torch.float32),
            edge_index=torch.tensor(edges, dtype=torch.long).t().contiguous(),
            node_type=torch.tensor(nodes['types'], dtype=torch.long)
        )

    def _create_nodes(self, state):
        """Map containers/processes to graph nodes with 192-dim features"""
        node_features = []
        node_types = []
        node_map = {}
        node_idx = 0

        # Create SystemNodes (one per container)
        for container in state['containers']:
            features = self._encode_system_node(container, state)
            node_features.append(features)
            node_types.append(self.NODE_TYPES['SystemNode'])
            node_map[container['name']] = node_idx
            node_idx += 1

        # Create ConnectionNodes (one per open port)
        for container_name, ports in state['connections'].items():
            if isinstance(ports, list):
                for port in ports:
                    features = self._encode_connection_node(port, container_name)
                    node_features.append(features)
                    node_types.append(self.NODE_TYPES['ConnectionNode'])
                    node_idx += 1

        return {
            'features': node_features,
            'types': node_types,
            'node_map': node_map
        }

    def _encode_system_node(self, container, state):
        """
        Encode container as 192-dim feature vector matching trained agent format:
        
        Structure:
        [0:4]     - node type one-hot (SystemNode=1 at idx 0)
        [4:174]   - SystemNode features (architecture, OS, patches, role flags)
        [174:183] - subnet membership (9-dim one-hot for which subnet)
        [183:185] - tabular features (compromised=0, scanned=0)
        [185:188] - message features (was_scanned=0, was_compromised=0, is_received=0)
        [188:192] - padding to match exact 192
        """
        features = [0.0] * 192

        # [0:4] Node type one-hot (SystemNode)
        features[0] = 1.0

        # [4:174] SystemNode-specific features
        # We don't have full CybORG data, so use heuristics:
        offset = 4

        # Architecture (x86/ARM) - assume x86
        features[offset] = 1.0  # x86
        offset += 10  # Skip remaining architecture dims

        # OS Distribution - infer from image name
        name_lower = container['image'].lower()
        if 'alpine' in name_lower:
            features[offset + 5] = 1.0  # Alpine
        elif 'ubuntu' in name_lower:
            features[offset + 3] = 1.0  # Ubuntu
        elif 'debian' in name_lower:
            features[offset + 2] = 1.0  # Debian
        elif 'postgres' in name_lower:
            features[offset + 6] = 1.0  # Postgres (has its own OS)
        else:
            features[offset] = 1.0  # Unknown
        offset += 15  # Skip OS dist dims

        # OS Type (Linux/Windows) - assume Linux
        features[offset + 1] = 1.0  # Linux
        offset += 5

        # OS Version - default to unknown
        offset += 20

        # OS Kernel Version - default
        offset += 15

        # OS Patches - no patches applied
        offset += 30

        # crown_jewel flag (1 scalar)
        container_name = container['name'].lower()
        features[offset] = 1.0 if 'database' in container_name else 0.0
        offset += 1

        # user flag (1 scalar)
        features[offset] = 1.0 if ('user' in container_name or 'admin' in container_name) else 0.0
        offset += 1

        # server flag (1 scalar)
        features[offset] = 1.0 if ('server' in container_name or 'web' in container_name or 'database' in container_name) else 0.0
        offset += 1

        # router flag (1 scalar)  
        features[offset] = 0.0  # None of our containers are routers
        offset += 1

        # [174:183] Subnet membership (9-dim one-hot)
        # Map containers to subnets (0-8, agent trained on 9 subnets)
        subnet_idx = self._get_subnet_idx(container_name)
        features[174 + subnet_idx] = 1.0

        # [183:185] Tabular features from EnterpriseMAE wrapper
        # compromised flag, scanned flag
        # We don't have this data from containerlab, so default to NOT compromised
        features[183] = 0.0  # not compromised (yet)
        features[184] = 0.0  # not scanned (yet)

        # [185:188] Message features from other agents
        # was_scanned, was_compromised, is_received
        features[185] = 0.0
        features[186] = 0.0  
        features[187] = 0.0  # no message received

        return features

    def _get_subnet_idx(self, container_name):
        """Map container to subnet index (0-8)"""
        name_lower = container_name.lower()
        if 'admin' in name_lower:
            return 0  # admin subnet
        elif 'operational' in name_lower or 'web-server' in name_lower or 'database' in name_lower:
            return 1  # operational subnet
        elif 'public' in name_lower:
            return 2  # public subnet  
        elif 'contractor' in name_lower:
            return 3
        elif 'attacker' in name_lower or 'internet' in name_lower:
            return 8  # internet subnet
        else:
            return 0  # default

    def _encode_connection_node(self, port, container_name):
        """
        Encode network connection as 192-dim feature vector
        
        Structure:
        [0:4]     - node type one-hot (ConnectionNode=1 at idx 1)
        [4:174]   - zeros (SystemNode features, not applicable)
        [174:214] - ConnectionNode features (process_name, process_type, flags)
        [214:223] - subnet membership
        [223:225] - tabular (not applicable to connections)
        [225:228] - messages (not applicable)
        [228:192] - padding
        """
        features = [0.0] * 192

        # [0:4] Node type one-hot (ConnectionNode)
        features[1] = 1.0

        # Skip SystemNode features [4:174]

        # [174:214] ConnectionNode features
        offset = 174

        # Process name (20-dim one-hot) - infer from port
        try:
            port_num = int(port)
            if port_num == 22:
                features[offset + 5] = 1.0  # SSH
            elif port_num == 80:
                features[offset + 1] = 1.0  # Apache
            elif port_num == 443:
                features[offset + 2] = 1.0  # HTTPS
            elif port_num == 5432:
                features[offset + 10] = 1.0  # Postgres
            elif port_num == 3306:
                features[offset + 11] = 1.0  # MySQL
            else:
                features[offset] = 1.0  # Unknown
        except:
            features[offset] = 1.0
        offset += 20

        # Process type (10-dim one-hot)
        try:
            port_num = int(port)
            if port_num in [80, 443]:
                features[offset + 3] = 1.0  # WebServer
            elif port_num in [22]:
                features[offset + 1] = 1.0  # SSH
            elif port_num in [5432, 3306]:
                features[offset + 5] = 1.0  # Database
            else:
                features[offset] = 1.0  # Unknown
        except:
            features[offset] = 1.0
        offset += 10

        # Flags (4 scalars)
        features[offset] = 0.0  # not suspicious_pid
        features[offset + 1] = 0.0  # not is_decoy
        features[offset + 2] = 1.0 if port in ['22', '80', '443', '5432'] else 0.0  # is_default service
        features[offset + 3] = 1.0 if (port.isdigit() and int(port) > 49152) else 0.0  # is_ephemeral

        return features

    def _create_edges(self, state, nodes):
        """
        Create edges between nodes
        - SystemNode to ConnectionNode (container has process with port)
        - SystemNode to SystemNode (network connectivity)
        """
        edge_list = []
        node_map = nodes['node_map']
        num_containers = len(state['containers'])

        # Edges between containers (fully connected for now)
        for i in range(num_containers):
            for j in range(num_containers):
                if i != j:
                    edge_list.append([i, j])

        # Edges from SystemNodes to their ConnectionNodes
        connection_idx = num_containers
        for container_name, ports in state['connections'].items():
            if isinstance(ports, list) and container_name in node_map:
                system_idx = node_map[container_name]
                for port in ports:
                    edge_list.append([system_idx, connection_idx])
                    edge_list.append([connection_idx, system_idx])
                    connection_idx += 1

        return edge_list if edge_list else [[0, 0]]
