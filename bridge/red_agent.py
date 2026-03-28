import docker

CLAB_PREFIX = "clab-cage4-defense-network-"

ACTION_NAMES = [
    DiscoverRemoteSystems,          #0
    AggressiveServiceDiscovery,     #1
    StealthServiceDiscovery,        #2
    DiscoverDeception,              #3
    ExploitRemoteService,           #4
    PrivilegeEscalate,              #5
    Impact,                         #6
    DegradeServices,                #7
    Withdraw                        #8
]


class RedAgent:
    def __init__(self, containers, decoys = None):
        self.client = docker.from_env()
        self.decoys = decoys or {}

        self.host_states = {}
        for c in containers:
            self.host_states[c["clean_name"]] = {"state": 'K'}  # K = Known, KD = Known Deception, S = Scanned, SD = Scanned Deception, U = User Access, UD = User Access Deception, R = Root Access, RD = Root Access Deception, F = Failed

        self.state_transitions_success = self._build_success_matrix()
        self.state_transitions_failure = self._build_failure_matrix()
        self.state_transitions_probability    = self._build_probability_matrix()


    def _build_success_matrix(self):
        map = {
            'K'  : ['KD', 'S',  'S',  None, None, None, None, None, None],
            'KD' : ['KD', 'SD', 'SD',  None, None, None, None, None, None],
            'S'  : ['SD', None, None, 'S' , 'U' , None, None, None, None],
            'SD' : ['SD', None, None, 'SD', 'UD', None, None, None, None],
            'U'  : ['UD', None, None, None, None, 'R' , None, None, 'S' ],
            'UD' : ['UD', None, None, None, None, 'RD', None, None, 'SD'],
            'R'  : ['RD', None, None, None, None, None, 'R' , 'R' , 'S' ],
            'RD' : ['RD', None, None, None, None, None, 'RD', 'RD', 'SD'],
            'F'  : ['F',  None, None, None, None, None, None, None, None],
        }
        return map
    
    def _build_failure_matrix(self):
        map = {
            'K'  : ['K' , 'K' , 'K' , None, None, None, None, None, None],
            'KD' : ['KD', 'KD', 'KD', None, None, None, None, None, None],
            'S'  : ['S' , None, None, 'S' , 'S' , None, None, None, None],
            'SD' : ['SD', None, None, 'SD', 'SD', None, None, None, None],
            'U'  : ['U' , None, None, None, None, 'U' , None, None, 'U' ],
            'UD' : ['UD', None, None, None, None, 'UD', None, None, 'UD'],
            'R'  : ['R' , None, None, None, None, None, 'R' , 'R' , 'R' ],
            'RD' : ['RD', None, None, None, None, None, 'RD', 'RD', 'RD'],
            'F'  : ['F',  None, None, None, None, None, None, None, None],
        }
        return map
    
    def _build_probability_matrix(self):    
        map = {
            'K'  : [0.5,  0.25, 0.25, None, None, None, None, None, None],
            'KD' : [None, 0.5,  0.5,  None, None, None, None, None, None],
            'S'  : [0.25, None, None, 0.25, 0.5 , None, None, None, None],
            'SD' : [None, None, None, 0.25, 0.75, None, None, None, None],
            'U'  : [0.5 , None, None, None, None, 0.5 , None, None, 0.0 ],
            'UD' : [None, None, None, None, None, 1.0 , None, None, 0.0 ],
            'R'  : [0.5,  None, None, None, None, None, 0.25, 0.25, 0.0 ],
            'RD' : [None, None, None, None, None, None, 0.5,  0.5,  0.0 ],
        }
        return map