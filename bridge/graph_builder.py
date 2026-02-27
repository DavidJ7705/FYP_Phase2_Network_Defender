FEATURE_DIM = 192

NODE_TYPES = {
    "SystemNode":0,
    "ConnectionNode":1,
    "FileNode":2,
    "InternetNode":3,
}

NUM_ROUTERS = 9

CONTAINER_ROLES ={
    "admin-ws": ("user", 0, 0),
    "web-server": ("server", 0, 4),
    "database": ("server", 1, 5),
    "public-web": ("server", 2, 6),
    #maybe attacker one too
}

# subnets in alphabetical order - gotten from inspect_weights.py
# [178]  admin_network_subnet_router
# [179]  contractor_network_subnet_router
# [180]  internet_subnet_router
# [181]  office_network_subnet_router
# [182]  operational_zone_a_subnet_router
# [183]  operational_zone_b_subnet_router
# [184]  public_access_zone_subnet_router
# [185]  restricted_zone_a_subnet_router
# [186]  restricted_zone_b_subnet_router
# [187]  tabular: was_compromised

class ObservationGraphBuilder:
    def build_graph(self, network_state):
        raise NotImplementedError

    def encode_host(self, container, role, subnet_idx):
        features = [0.0] * FEATURE_DIM

        features[14] = 1.0 #ubuntu
        features[24] = 1.0 #linux

        if role == "server":
            features[56] = 1.0 #server
        else:
            features[55] = 1.0 #user

        features[178 +subnet_idx] = 1.0

        if container.get("is_compromised"):
            features[187] = 1.0
            features[188] = 1.0
        
        return features
    
