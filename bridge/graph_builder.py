class ObservationGraphBuilder:
    """
    Build graph matching CybORG's EXACT structure (86 nodes, ~172 edges)
    by padding with dummy nodes
    """

    # CybORG's actual structure
    TARGET_NUM_NODES = 86
    TARGET_NUM_EDGES = 172

    def build_graph(self, network_state):
        """Create graph with padded structure matching CybORG"""
        import torch
        from torch_geometric.data import Data

        # Step 1: Create real nodes
        real_nodes = self._create_real_nodes(network_state)

        # Step 2: Create dummy nodes to reach 86 total
        all_nodes = self._pad_to_target_size(real_nodes)

        # Step 3: Create edges (real + dummy)
        edges = self._create_edges_with_padding(network_state, real_nodes, all_nodes)

        return Data(
            x=torch.tensor(all_nodes['features'], dtype=torch.float32),
            edge_index=torch.tensor(edges, dtype=torch.long).t().contiguous(),
            node_type=torch.tensor(all_nodes['types'], dtype=torch.long),
            num_real=all_nodes['num_real']  # Helps AgentAdapter locate dummy nodes
        )

    def _create_real_nodes(self, state):
        """Create actual container/port nodes"""
        features = []
        types = []
        node_map = {}
        idx = 0

        # Containers
        for container in state['containers']:
            feat = self._encode_system_node_cyborg_style(container)
            features.append(feat)
            types.append(0)
            node_map[container['name']] = idx
            idx += 1

        # Ports
        for container_name, ports in state['connections'].items():
            if isinstance(ports, list):
                for port in ports:
                    feat = self._encode_connection_node_cyborg_style(port)
                    features.append(feat)
                    types.append(1)
                    idx += 1

        return {
            'features': features,
            'types': types,
            'node_map': node_map,
            'count': idx
        }

    def _pad_to_target_size(self, real_nodes):
        """Add dummy nodes to reach 86 nodes total"""
        features = real_nodes['features'].copy()
        types = real_nodes['types'].copy()
        
        num_real = real_nodes['count']
        num_dummy = self.TARGET_NUM_NODES - num_real
        
        print(f"   Adding {num_dummy} dummy nodes ({num_real} real → {self.TARGET_NUM_NODES} total)")
        
        # Add dummy router nodes (positions 0,55,57,178,191 like CybORG routers)
        for i in range(min(9, num_dummy)):
            dummy_router = [0.0] * 200
            dummy_router[0] = 1.0   # SystemNode
            dummy_router[55] = 1.0  # OS feature
            dummy_router[57] = 1.0  # OS feature  
            dummy_router[178] = 1.0 # subnet
            dummy_router[191] = -1.0 # self message
            features.append(dummy_router)
            types.append(0)
        
        # Add dummy server/user nodes for remaining slots
        remaining = num_dummy - 9
        for i in range(remaining):
            if i % 2 == 0:  # Server
                dummy = [0.0] * 200
                dummy[0] = 1.0
                dummy[5] = 1.0
                dummy[24] = 1.0
                dummy[25] = 1.0
                dummy[56] = 1.0  # server flag
                dummy[178 + (i % 9)] = 1.0  # subnet
                features.append(dummy)
                types.append(0)
            else:  # User
                dummy = [0.0] * 200
                dummy[0] = 1.0
                dummy[5] = 1.0
                dummy[24] = 1.0
                dummy[25] = 1.0
                dummy[55] = 1.0  # user flag
                dummy[178 + (i % 9)] = 1.0  # subnet
                features.append(dummy)
                types.append(0)
        
        return {
            'features': features,
            'types': types,
            'node_map': real_nodes['node_map'],
            'num_real': num_real
        }

    def _create_edges_with_padding(self, state, real_nodes, all_nodes):
        """Create edges matching CybORG's ~172 edges"""
        edges = []
        num_real = real_nodes['count']
        num_total = self.TARGET_NUM_NODES
        
        # Real edges (container-to-container, container-to-port)
        node_map = real_nodes['node_map']
        num_containers = len(state['containers'])
        
        for i in range(num_containers):
            for j in range(num_containers):
                if i != j:
                    edges.append([i, j])
        
        connection_idx = num_containers
        for container_name, ports in state['connections'].items():
            if isinstance(ports, list) and container_name in node_map:
                system_idx = node_map[container_name]
                for port in ports:
                    edges.append([system_idx, connection_idx])
                    edges.append([connection_idx, system_idx])
                    connection_idx += 1
        
        # Dummy edges to pad to ~172 edges
        # Connect dummy nodes to each other in a ring topology
        current_edge_count = len(edges)
        needed_edges = self.TARGET_NUM_EDGES - current_edge_count
        
        print(f"   Adding ~{needed_edges} dummy edges ({current_edge_count} real → ~{self.TARGET_NUM_EDGES} total)")
        
        for i in range(num_real, num_total - 1):
            if len(edges) >= self.TARGET_NUM_EDGES:
                break
            # Ring: connect i to i+1
            edges.append([i, i + 1])
            edges.append([i + 1, i])
        
        # Connect last dummy to first dummy
        if len(edges) < self.TARGET_NUM_EDGES and num_total > num_real:
            edges.append([num_total - 1, num_real])
            edges.append([num_real, num_total - 1])
        
        # Add more cross-connections if still need edges
        for i in range(num_real, num_total - 2):
            if len(edges) >= self.TARGET_NUM_EDGES:
                break
            edges.append([i, i + 2])
            edges.append([i + 2, i])
        
        return edges if edges else [[0, 0]]

    def _encode_system_node_cyborg_style(self, container):
        """Same as v3 - encode with compromise flags"""
        features = [0.0] * 200
        name = container['name'].lower()
        
        features[0] = 1.0
        features[5] = 1.0
        features[24] = 1.0
        features[25] = 1.0
        
        is_server = ('server' in name or 'web' in name or 'database' in name or 'db' in name)
        if is_server:
            features[56] = 1.0
        else:
            features[55] = 1.0
        
        subnet_idx = self._get_subnet_idx(name)
        features[174 + subnet_idx] = 1.0  # Corrected from 178 to 174 to match 192-dim schema
        
        # COMPROMISE FLAGS
        # Ideally, we set features[183] = 1.0 for Compromised
        if container.get('is_compromised', False):
            # Set standard compromised flag
            features[183] = 1.0
            
            # Keep the "Super Compromised" triggers found via brute force, 
            # as they might correspond to specific learned features (e.g., OS version, specific vulnerability state)
            features[57] = -1.0
            features[184] = -1.0
            features[186] = -1.0
            features[179] = -1.0
            features[187] = 1.0

            # Additional booster
            features[102] = 1.0
            features[91] = -1.0
            features[56] = -1.0
            
            features[188] = 1.0 
        else:
            # Reset to safe values
            features[57] = 1.0
            features[184] = 0.0 # Or 1.0? Inspect said 1.0 usually. 
            features[183] = 0.0
            features[186] = 0.0
            features[179] = 0.0
            features[187] = 0.0
        
        return features

    def _get_subnet_idx(self, container_name):
        """Map to subnet 0-8"""
        name = container_name.lower()
        if 'admin' in name:
            return 0
        elif 'web-server' in name or 'database' in name:
            return 1
        elif 'public' in name:
            return 2
        elif 'attacker' in name:
            return 8
        else:
            return 0

    def _encode_connection_node_cyborg_style(self, port):
        """Same as v3"""
        features = [0.0] * 200
        features[0] = 1.0
        features[55] = 1.0
        features[57] = 1.0
        features[179] = 1.0
        return features
