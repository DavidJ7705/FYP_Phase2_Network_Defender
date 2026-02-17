import random
import logging

logger = logging.getLogger(__name__)


class CAGE4RedAgent:
    """FSM-based red agent matching CybORG CAGE4's FiniteStateRedAgent.

    FSM States:
    - K (Known): Host discovered via reconnaissance
    - S (Scanned): Services enumerated
    - U (User): User-level compromise achieved
    - R (Root): Root-level compromise achieved

    State Transitions:
    K --scan--> S --exploit--> U --escalate--> R --impact/degrade--> R
    """

    # FSM states
    STATE_KNOWN = 'K'
    STATE_SCANNED = 'S'
    STATE_USER = 'U'
    STATE_ROOT = 'R'

    def __init__(self, client):
        self.client = client
        self.host_states = {}  # {hostname: {'state': str, 'subnet': str}}
        self._init_contractor_network()

    def _init_contractor_network(self):
        """Start with contractor network visible (entry point like CybORG)"""
        contractor_hosts = [
            'contractor-network-server-0',
            'contractor-network-user-0',
            'contractor-network-user-1'
        ]
        for host in contractor_hosts:
            self.host_states[host] = {
                'state': self.STATE_KNOWN,
                'subnet': 'contractor_network'
            }
        logger.info(f"RED AGENT: Initialized with contractor network visible ({len(contractor_hosts)} hosts)")

    def attack(self, probability=0.5):
        """Execute one FSM transition.

        Args:
            probability: Chance of executing an attack this turn

        Returns:
            Target hostname if attack executed, None otherwise
        """
        if random.random() > probability:
            return None

        target = self._choose_target()
        if not target:
            logger.info("RED AGENT: No available targets")
            return None

        action = self._get_action_for_state(target)
        success = self._execute_action(target, action)

        if success:
            self._transition_state(target, action)
            if action == 'exploit':
                # Lateral movement - discover adjacent subnets
                self._discover_neighbors(target)

        return target

    def _choose_target(self):
        """Select target prioritizing FSM progression: K > S > U > R"""
        for state in [self.STATE_KNOWN, self.STATE_SCANNED,
                      self.STATE_USER, self.STATE_ROOT]:
            targets = [h for h, s in self.host_states.items()
                      if s['state'] == state]
            if targets:
                return random.choice(targets)
        return None

    def _get_action_for_state(self, target):
        """Determine action based on current FSM state"""
        state = self.host_states[target]['state']

        if state == self.STATE_KNOWN:
            return 'scan'
        elif state == self.STATE_SCANNED:
            return 'exploit'
        elif state == self.STATE_USER:
            return 'escalate'
        elif state == self.STATE_ROOT:
            # Impact or degrade services on compromised hosts
            return random.choice(['impact', 'degrade'])

        return 'scan'  # Fallback

    def _execute_action(self, target, action):
        """Execute action in containerlab container"""
        clab_name = f"clab-cage4-defense-network-{target}"

        try:
            container = self.client.containers.get(clab_name)

            if action == 'scan':
                # Service discovery (like CybORG's DiscoverNetworkServices)
                container.exec_run(['/bin/sh', '-c', 'netstat -tuln'])
                logger.info(f"RED AGENT [SCAN]: Enumerated services on {target}")
                return True

            elif action == 'exploit':
                # Initial compromise (plant IOC)
                container.exec_run(['/bin/sh', '-c', 'touch /tmp/pwned'])
                logger.info(f"RED AGENT [EXPLOIT]: Compromised {target} (IOC: /tmp/pwned)")
                return True

            elif action == 'escalate':
                # Privilege escalation
                container.exec_run(['/bin/sh', '-c', 'touch /tmp/pwned_root'])
                logger.info(f"RED AGENT [ESCALATE]: Gained root on {target}")
                return True

            elif action == 'impact':
                # Data exfiltration
                container.exec_run(['/bin/sh', '-c', 'cp /etc/passwd /tmp/exfil_passwd'])
                logger.info(f"RED AGENT [IMPACT]: Exfiltrated data from {target}")
                return True

            elif action == 'degrade':
                # Service degradation
                container.exec_run(['/bin/sh', '-c', 'pkill nginx || pkill apache2 || true'])
                logger.info(f"RED AGENT [DEGRADE]: Disrupted services on {target}")
                return True

            return False

        except Exception as e:
            logger.error(f"RED AGENT: Failed to {action} {target}: {e}")
            return False

    def _transition_state(self, target, action):
        """Update FSM state after successful action"""
        transitions = {
            'scan': self.STATE_SCANNED,
            'exploit': self.STATE_USER,
            'escalate': self.STATE_ROOT,
            # impact/degrade keep state at ROOT
        }

        if action in transitions:
            old_state = self.host_states[target]['state']
            new_state = transitions[action]
            self.host_states[target]['state'] = new_state
            logger.info(f"RED AGENT: {target} state: {old_state} → {new_state}")

    def _discover_neighbors(self, compromised_host):
        """Lateral movement - discover hosts in adjacent subnets (CybORG-style)"""
        subnet = self.host_states[compromised_host]['subnet']

        # CybORG topology-aware adjacency
        adjacency = {
            'contractor_network': [
                'restricted_zone_a',
                'restricted_zone_b',
                'public_access_zone'
            ],
            'restricted_zone_a': [
                'operational_zone_a'
            ],
            'restricted_zone_b': [
                'operational_zone_b'
            ],
            'public_access_zone': [
                'admin_network',
                'office_network'
            ],
            # Operational zones are dead-ends (no further lateral movement)
        }

        neighbors = adjacency.get(subnet, [])
        for neighbor_subnet in neighbors:
            self._add_subnet_hosts(neighbor_subnet)

    def _add_subnet_hosts(self, subnet_name):
        """Add all hosts in a subnet to known state (reconnaissance)"""
        subnet_map = {
            'restricted_zone_a': [
                'restricted-zone-a-server-0',
                'restricted-zone-a-server-1',
                'restricted-zone-a-user-0'
            ],
            'operational_zone_a': [
                'operational-zone-a-server-0',
                'operational-zone-a-user-0'
            ],
            'restricted_zone_b': [
                'restricted-zone-b-server-0',
                'restricted-zone-b-user-0'
            ],
            'operational_zone_b': [
                'operational-zone-b-server-0',
                'operational-zone-b-user-0'
            ],
            'public_access_zone': [
                'public-access-zone-user-0'
            ],
            'admin_network': [
                'admin-network-user-0'
            ],
            'office_network': [
                'office-network-user-0',
                'office-network-user-1'
            ],
        }

        hosts = subnet_map.get(subnet_name, [])
        new_discoveries = 0

        for host in hosts:
            if host not in self.host_states:
                self.host_states[host] = {
                    'state': self.STATE_KNOWN,
                    'subnet': subnet_name
                }
                new_discoveries += 1

        if new_discoveries > 0:
            logger.info(f"RED AGENT [LATERAL MOVEMENT]: Discovered {new_discoveries} hosts in {subnet_name}")

    def get_fsm_summary(self):
        """Return current FSM state distribution for logging"""
        counts = {
            self.STATE_KNOWN: 0,
            self.STATE_SCANNED: 0,
            self.STATE_USER: 0,
            self.STATE_ROOT: 0,
        }

        for host_info in self.host_states.values():
            state = host_info['state']
            counts[state] += 1

        return counts
