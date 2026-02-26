FEATURE_DIM = 192

NODE_TYPES = {
    "SystemNode":0,
    "ConnectionNode":1,
    "FileNode":2,
    "InternetNode":3,
}

NUM_ROUTERS = 9

CONTAINER_ROLES ={
    "admin-ws": ("user", 0),
    "web-server": ("server", 0),
    "database": ("server", 1),
    "public-web": ("server", 2),
    #maybe attacker one too
}

class ObservationGraphBuilder:
    def build_graph(self, network_state):
        raise NotImplementedError
    
