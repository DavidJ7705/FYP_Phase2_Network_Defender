# mac: venv/bin/python -m Integration.Mininet.mininet_cyborg_simplified
# windows: .\venv\Scripts\python -m Integration.Mininet.mininet_cyborg_simplified


"""
2 switches, 1 server, 2 users (3 hosts, 1 subnet)
"""

from mininet.topo import Topo


class CybORGSimplifiedTopo(Topo):
    """CybORG topology v1 - Simple baseline"""
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)
        
        # ========== SWITCHES (representing subnets) ==========
        admin_switch = self.addSwitch('s1')
        operational_switch = self.addSwitch('s2')
        
        # ========== HOSTS (representing devices) ==========
        admin_server = self.addHost('as1', ip='192.168.1.10/24')
        admin_user = self.addHost('au1', ip='192.168.1.20/24')
        operational_user = self.addHost('ousr', ip='192.168.1.30/24')

        # ========== LINKS (representing connections) ==========
        self.addLink(admin_switch, admin_server)
        self.addLink(admin_switch, admin_user)
        self.addLink(operational_switch, operational_user)
        self.addLink(admin_switch, operational_switch)

topos = {'cyborg_simplified': (lambda: CybORGSimplifiedTopo())}

# sudo mn --custom ~/mininet_cyborg_simplified.py --topo cyborg_simplified