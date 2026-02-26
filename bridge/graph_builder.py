FEATURE_DIM = 192

NODE_TYPES = {
    "SystemNode":0,
    "ConnectionNode":1,
    "FileNode":2,
    "InternetNode":3,
}

NUM_ROUTERS = 9

class ObservationGraphBuilder:
    def build_graph(self, network_state):
        raise NotImplementedError
    
