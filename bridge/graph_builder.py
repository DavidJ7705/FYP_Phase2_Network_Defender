class ObservationGraphBuilder:
    """
    Build graph matching CybORG's router-mediated structure with 9 real routers.
    Hosts connect only to their subnet routers, routers connect to each other.
    """

    def __init__(self):
        # Import CONTAINER_ROLES to align classification with agent expectations
        from agent_adapter import CONTAINER_ROLES
        self.container_roles = CONTAINER_ROLES

    def build_graph(self, network_state):
        """Create graph with router-mediated connectivity"""
        import torch
        from torch_geometric.data import Data

        # Step 1: Classify nodes by type
        servers, users, routers = self._classify_nodes(network_state)

        print(f"   Classified: {len(servers)} servers, {len(users)} users, {len(routers)} routers")

        # Step 2: Create features (servers → users → routers)
        node_features = []
        node_features.extend([self._encode_server(s) for s in servers])
        node_features.extend([self._encode_user(u) for u in users])
        node_features.extend([self._encode_router(r) for r in routers])

        # Step 3: Build router-mediated edges
        edges = self._build_router_mediated_edges(servers, users, routers)

        # Debug: Check how many nodes have compromised flag set
        node_features_tensor = torch.tensor(node_features, dtype=torch.float32)
        compromised_count = (node_features_tensor[:, 183] == 1.0).sum().item()
        print(f"   Graph: {len(servers) + len(users) + len(routers)} nodes, {len(edges)} edges")
        print(f"   [GRAPH DEBUG] {compromised_count} nodes have feature[183]=1.0 (compromised flag)")

        return Data(
            x=torch.tensor(node_features, dtype=torch.float32),
            edge_index=torch.tensor(edges, dtype=torch.long).t().contiguous(),
            num_servers=len(servers),
            num_users=len(users),
            num_routers=len(routers),
        )

    def _classify_nodes(self, state):
        """Separate servers, users, and routers using CONTAINER_ROLES mapping"""
        servers = []
        users = []
        routers = []

        for container in state['containers']:
            name = container['name'].lower()

            # Remove containerlab prefix if present
            if 'clab-' in name:
                name = name.split('clab-')[1]
                if name.startswith('cage4-defense-network-'):
                    name = name.replace('cage4-defense-network-', '')
                elif name.startswith('fyp-defense-network-'):
                    name = name.replace('fyp-defense-network-', '')

            container['clean_name'] = name

            # Use CONTAINER_ROLES mapping for classification
            role_info = self.container_roles.get(name)

            if role_info is None:
                # Routers and excluded hosts (mapped to None)
                if 'router' in name:
                    routers.append(container)
                # Skip root-internet-host and others
            elif role_info[0] == 'server':
                servers.append(container)
            elif role_info[0] == 'user':
                users.append(container)

        return servers, users, routers

    def _build_router_mediated_edges(self, servers, users, routers):
        """Create edges: host → router → router → host (no direct host↔host)"""
        edges = []
        num_hosts = len(servers) + len(users)

        # Build mapping from container name to index
        node_map = {}
        for i, s in enumerate(servers):
            node_map[s['clean_name']] = i
        for i, u in enumerate(users):
            node_map[u['clean_name']] = num_hosts - len(users) + i
        for i, r in enumerate(routers):
            node_map[r['clean_name']] = num_hosts + i

        # 1. Host → Subnet Router (bidirectional)
        for host in servers + users:
            router_name = self._get_subnet_router(host['clean_name'])
            if router_name in node_map:
                host_idx = node_map[host['clean_name']]
                router_idx = node_map[router_name]
                edges.append([host_idx, router_idx])
                edges.append([router_idx, host_idx])

        # 2. Router → Router (CybORG topology)
        router_links = self._get_cyborg_router_links()
        for src_name, dst_names in router_links.items():
            if src_name in node_map:
                src_idx = node_map[src_name]
                for dst_name in dst_names:
                    if dst_name in node_map:
                        dst_idx = node_map[dst_name]
                        edges.append([src_idx, dst_idx])

        return edges if edges else [[0, 0]]

    def _get_subnet_router(self, hostname):
        """Get the router name for a given host"""
        # Extract subnet from hostname
        # e.g., "restricted-zone-a-server-0" → "restricted-zone-a-router"
        parts = hostname.split('-')

        # Find where the role (server/user) starts
        if 'server' in hostname:
            role_idx = hostname.index('server')
        elif 'user' in hostname:
            role_idx = hostname.index('user')
        else:
            return None

        # Everything before the role + "router"
        subnet_prefix = hostname[:role_idx].rstrip('-')
        return f"{subnet_prefix}-router"

    def _get_cyborg_router_links(self):
        """CybORG's router topology (matches _generate_data_links)"""
        return {
            'internet-router': [
                'restricted-zone-a-router',
                'restricted-zone-b-router',
                'contractor-network-router',
                'public-access-zone-router',
            ],
            'restricted-zone-a-router': [
                'internet-router',
                'operational-zone-a-router',
            ],
            'restricted-zone-b-router': [
                'internet-router',
                'operational-zone-b-router',
            ],
            'contractor-network-router': [
                'internet-router',
            ],
            'public-access-zone-router': [
                'internet-router',
                'admin-network-router',
                'office-network-router',
            ],
            'operational-zone-a-router': [
                'restricted-zone-a-router',
            ],
            'operational-zone-b-router': [
                'restricted-zone-b-router',
            ],
            'admin-network-router': [
                'public-access-zone-router',
            ],
            'office-network-router': [
                'public-access-zone-router',
            ],
        }

    def _encode_server(self, container):
        """Encode server node with CybORG feature positions"""
        features = [0.0] * 200
        name = container['clean_name']

        # Basic flags
        features[0] = 1.0   # SystemNode
        features[5] = 1.0   # Known host
        features[24] = 1.0  # Accessible
        features[25] = 1.0  # Privileged access
        features[56] = 1.0  # Server role

        # Subnet encoding
        subnet_idx = self._get_subnet_idx(name)
        features[174 + subnet_idx] = 1.0

        # Compromise flags
        is_compromised = container.get('is_compromised', False)
        if is_compromised:
            print(f"   [GRAPH DEBUG] Encoding COMPROMISED server {name}: feature[183]=1.0")
            features[183] = 1.0  # Compromised flag
            features[57] = -1.0  # Attack indicator
            features[184] = -1.0
            features[186] = -1.0
            features[179] = -1.0
            features[187] = 1.0
            features[102] = 1.0
            features[91] = -1.0
            features[56] = -1.0  # Override server flag
            features[188] = 1.0  # Scanned/attacked
        else:
            features[57] = 1.0
            features[184] = 0.0
            features[183] = 0.0
            features[186] = 0.0
            features[179] = 0.0
            features[187] = 0.0

        return features

    def _encode_user(self, container):
        """Encode user node with CybORG feature positions"""
        features = [0.0] * 200
        name = container['clean_name']

        # Basic flags
        features[0] = 1.0   # SystemNode
        features[5] = 1.0   # Known host
        features[24] = 1.0  # Accessible
        features[25] = 1.0  # Privileged access
        features[55] = 1.0  # User role (instead of server)

        # Subnet encoding
        subnet_idx = self._get_subnet_idx(name)
        features[174 + subnet_idx] = 1.0

        # Compromise flags (same as server)
        is_compromised = container.get('is_compromised', False)
        if is_compromised:
            print(f"   [GRAPH DEBUG] Encoding COMPROMISED user {name}: feature[183]=1.0")
            features[183] = 1.0
            features[57] = -1.0
            features[184] = -1.0
            features[186] = -1.0
            features[179] = -1.0
            features[187] = 1.0
            features[102] = 1.0
            features[91] = -1.0
            features[55] = -1.0  # Override user flag
            features[188] = 1.0
        else:
            features[57] = 1.0
            features[184] = 0.0
            features[183] = 0.0
            features[186] = 0.0
            features[179] = 0.0
            features[187] = 0.0

        return features

    def _encode_router(self, router):
        """Match CybORG router encoding exactly"""
        features = [0.0] * 200
        name = router['clean_name']

        features[0] = 1.0    # SystemNode
        features[55] = 1.0   # OS type
        features[57] = 1.0   # OS version
        features[178] = 1.0  # Subnet flag
        features[191] = -1.0 # Self message

        subnet_idx = self._get_router_subnet_idx(name)
        features[174 + subnet_idx] = 1.0

        return features

    def _get_subnet_idx(self, hostname):
        """Map hostname to subnet index 0-8"""
        if 'restricted-zone-a' in hostname:
            return 0
        elif 'operational-zone-a' in hostname:
            return 1
        elif 'restricted-zone-b' in hostname:
            return 2
        elif 'operational-zone-b' in hostname:
            return 3
        elif 'contractor-network' in hostname:
            return 4
        elif 'public-access-zone' in hostname:
            return 5
        elif 'admin-network' in hostname:
            return 6
        elif 'office-network' in hostname:
            return 7
        elif 'internet' in hostname:
            return 8
        else:
            return 0  # Default

    def _get_router_subnet_idx(self, router_name):
        """Map router name to subnet index 0-8"""
        return self._get_subnet_idx(router_name)
