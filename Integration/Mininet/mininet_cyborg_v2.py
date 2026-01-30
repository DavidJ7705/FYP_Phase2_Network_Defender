# mac: venv/bin/python -m Integration.Mininet.mininet_cyborg_v2
# windows: .\venv\Scripts\python -m Integration.Mininet.mininet_cyborg_v2


"""
version 2 of cyborg topology
(5 hosts, 2 subnet)
admin zone (10.0.110.0/24) - 2 hosts
operational zone (10.0.198.0/24) - 3 hosts
"""

from mininet.topo import Topo


class CybORGTopoV2(Topo):
    """CybORG topology v2 - 2 Zones, 5 Hosts"""
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)
        
        # ========== SWITCHES (representing zones in cyborg) ==========
        admin_switch = self.addSwitch('s1')
        operational_switch = self.addSwitch('s2')
        
        # ========== HOSTS (representing devices) ==========
        # admin zone (10.0.110.0/24)
        admin_server = self.addHost('asrv', ip='10.0.110.10/24')
        admin_user = self.addHost('ausr', ip='10.0.110.20/24')

        # operational zone (10.0.198.0/24)
        operational_server = self.addHost('osrv', ip='10.0.198.10/24')
        operational_user_1 = self.addHost('ousr1', ip='10.0.198.20/24')
        operational_user_2 = self.addHost('ousr2', ip='10.0.198.30/24')

        # ========== LINKS (representing connections) ==========
        # admin zone links
        self.addLink(admin_switch, admin_server)
        self.addLink(admin_switch, admin_user)

        # operational zone links
        self.addLink(operational_switch, operational_server)
        self.addLink(operational_switch, operational_user_1)
        self.addLink(operational_switch, operational_user_2)

        # connect switches
        self.addLink(admin_switch, operational_switch)

topos = {'cyborg_v2': (lambda: CybORGTopoV2())}

# sudo mn --custom ~/mininet_cyborg_v2.py --topo cyborg_v2