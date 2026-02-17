import logging
import random

logger = logging.getLogger(__name__)

CLAB_PREFIX = "clab-fyp-defense-network-"

# Network topology adjacency (who can reach who directly)
ADJACENCY = {
    "attacker":   ["public-web"],
    "public-web": ["attacker", "web-server"],
    "web-server": ["public-web", "database", "admin-ws"],
    "database":   ["web-server"],
    "admin-ws":   ["web-server"],
}

# IP addresses for each host (used in exfil/scan commands)
HOST_IPS = {
    "admin-ws":   "10.0.110.10",
    "web-server": "10.0.110.1",
    "database":   "10.0.198.10",
    "public-web": "10.0.178.10",
    "attacker":   "10.0.200.10",
}


class RedAgent:
    """
    Multi-stage adversary that follows a realistic kill chain:

    Phase 1 - Reconnaissance:  Port scan targets from attacker
    Phase 2 - Initial Access:  Exploit public-web (internet-facing)
    Phase 3 - Lateral Movement: Pivot through the network following adjacency
    Phase 4 - Escalation:      Deploy persistence, exfil data, open backdoors

    Each attack leaves specific IOCs that the blue agent must detect and remediate.
    """

    # Attack types and what IOCs they leave
    ATTACK_TYPES = {
        "exploit":     "Plant IOC flag file (/tmp/pwned)",
        "backdoor":    "Start background listener process",
        "exfiltrate":  "Copy sensitive files to /tmp/exfil_*",
        "persist":     "Install cron-based persistence",
        "scan":        "Port scan from compromised host",
    }

    def __init__(self, target_list, client=None):
        import docker
        self.client = client or docker.from_env()
        self.targets = target_list
        self.compromised = set()       # Currently compromised hosts
        self.phase = 0                 # Kill chain phase
        self.step_count = 0            # Track progression
        self.attack_log = []           # History of all attacks
        logger.info(f"RED AGENT: Initialized. Targets: {self.targets}")
        logger.info(f"   Kill chain: Recon -> Initial Access -> Lateral Movement -> Escalation")

    def _resolve_container(self, host):
        """Resolve short name to full containerlab container name."""
        full_name = f"{CLAB_PREFIX}{host}"
        return self.client.containers.get(full_name)

    def _exec(self, host, cmd):
        """Execute a command on a container. Returns (exit_code, output_str)."""
        try:
            container = self._resolve_container(host)
            exit_code, output = container.exec_run(['/bin/sh', '-c', cmd])
            return exit_code, output.decode().strip()
        except Exception as e:
            return -1, str(e)

    # ── Attack Methods ────────────────────────────────────────────

    def _exploit(self, target):
        """Plant the IOC flag file - basic compromise indicator."""
        code, _ = self._exec(target, 'touch /tmp/pwned')
        if code == 0:
            self.compromised.add(target)
            return True, "IOC planted (/tmp/pwned)"
        return False, "Failed to plant IOC"

    def _backdoor(self, target):
        """Start a background nc listener as a backdoor process."""
        port = random.randint(4440, 4450)
        # Start nc listener in background, log to file
        cmd = f'nc -l -p {port} > /tmp/backdoor_{port}.log 2>&1 & echo $!'
        code, output = self._exec(target, cmd)
        if code == 0:
            # Also plant IOC so detection picks it up
            self._exec(target, 'touch /tmp/pwned')
            self.compromised.add(target)
            return True, f"Backdoor listener on port {port} (PID: {output})"
        return False, "Failed to start backdoor"

    def _exfiltrate(self, target):
        """Copy sensitive files to /tmp - simulates data staging for exfil."""
        cmd = (
            'cp /etc/passwd /tmp/exfil_passwd 2>/dev/null; '
            'cp /etc/shadow /tmp/exfil_shadow 2>/dev/null; '
            'echo "EXFIL_READY" > /tmp/exfil_flag; '
            'touch /tmp/pwned'
        )
        code, _ = self._exec(target, cmd)
        if code == 0:
            self.compromised.add(target)
            return True, "Staged /etc/passwd + /etc/shadow for exfiltration"
        return False, "Failed to stage data"

    def _persist(self, target):
        """Install persistence via cron/periodic scripts."""
        cmd = (
            'mkdir -p /etc/periodic/15min 2>/dev/null; '
            'echo "#!/bin/sh\ntouch /tmp/pwned" > /etc/periodic/15min/backdoor.sh; '
            'chmod +x /etc/periodic/15min/backdoor.sh; '
            'touch /tmp/pwned'
        )
        code, _ = self._exec(target, cmd)
        if code == 0:
            self.compromised.add(target)
            return True, "Persistence installed (/etc/periodic/15min/backdoor.sh)"
        return False, "Failed to install persistence"

    def _scan(self, source, target_ip):
        """Port scan from a compromised host to a target IP."""
        # Quick scan of common ports using nc with timeout
        ports = [22, 80, 443, 5432, 8080]
        cmd = '; '.join(
            f'(echo >/dev/tcp/{target_ip}/{p} 2>/dev/null && echo "OPEN:{p}") || true'
            for p in ports
        )
        # Fallback: use nc if /dev/tcp not available (Alpine/busybox)
        cmd = '; '.join(
            f'(nc -z -w1 {target_ip} {p} 2>/dev/null && echo "OPEN:{p}") || true'
            for p in ports
        )
        code, output = self._exec(source, cmd)
        open_ports = [line for line in output.split('\n') if 'OPEN' in line]
        return True, f"Scanned {target_ip} from {source}: {open_ports if open_ports else 'no open ports found'}"

    # ── Kill Chain Orchestration ──────────────────────────────────

    def attack(self, probability=0.5):
        """
        Execute the next phase of the kill chain.
        Each call advances the attack, creating a realistic multi-stage intrusion.
        """
        self.step_count += 1

        # Random decision: attack this step?
        if random.random() > probability:
            return None

        # Remove hosts from compromised set if they were restored (IOC gone)
        self._refresh_compromised()

        # Pick attack based on current phase
        if self.phase == 0:
            result = self._phase_recon()
        elif self.phase == 1:
            result = self._phase_initial_access()
        elif self.phase == 2:
            result = self._phase_lateral_movement()
        else:
            result = self._phase_escalation()

        return result

    def _refresh_compromised(self):
        """Check which hosts are still compromised (IOC still present)."""
        still_compromised = set()
        for host in list(self.compromised):
            code, _ = self._exec(host, 'test -f /tmp/pwned')
            if code == 0:
                still_compromised.add(host)
            else:
                logger.info(f"   RED AGENT: {host} was cleaned by blue team!")
        removed = self.compromised - still_compromised
        if removed:
            # If blue team cleaned our access, we may need to re-compromise
            logger.info(f"   RED AGENT: Lost access to: {removed}")
            # Regress phase if we lost our foothold
            if not still_compromised and self.phase > 1:
                self.phase = 1
                logger.info(f"   RED AGENT: Lost all footholds! Regressing to Phase 1")
        self.compromised = still_compromised

    def _phase_recon(self):
        """Phase 0: Reconnaissance - scan the network from attacker."""
        logger.info(f"\nRED AGENT [Phase 0 - RECON]: Scanning network...")

        # Scan public-web (the only host attacker can reach)
        target_ip = HOST_IPS["public-web"]
        success, msg = self._scan("attacker", target_ip)
        self._log_attack("scan", "attacker", "public-web", msg)
        logger.info(f"   {msg}")

        # Advance to initial access
        self.phase = 1
        logger.info(f"   RED AGENT: Recon complete. Advancing to Phase 1 (Initial Access)")
        return "public-web"

    def _phase_initial_access(self):
        """Phase 1: Exploit the internet-facing server (public-web)."""
        target = "public-web"

        if target in self.compromised:
            # Already have access, advance
            self.phase = 2
            logger.info(f"\nRED AGENT [Phase 1 - INITIAL ACCESS]: Already have access to {target}, advancing...")
            return self._phase_lateral_movement()

        logger.info(f"\nRED AGENT [Phase 1 - INITIAL ACCESS]: Exploiting {target}...")

        # Exploit public-web
        success, msg = self._exploit(target)
        self._log_attack("exploit", "attacker", target, msg)

        if success:
            logger.info(f"   EXPLOIT SUCCESS: {msg}")
            self.phase = 2
            logger.info(f"   RED AGENT: Foothold established! Advancing to Phase 2 (Lateral Movement)")
        else:
            logger.info(f"   EXPLOIT FAILED: {msg}")

        return target

    def _phase_lateral_movement(self):
        """Phase 2: Pivot through the network from compromised hosts."""
        # Find reachable targets from our compromised hosts
        reachable_targets = set()
        for host in self.compromised:
            for neighbor in ADJACENCY.get(host, []):
                if neighbor not in self.compromised and neighbor != "attacker":
                    reachable_targets.add((host, neighbor))

        if not reachable_targets:
            # All reachable targets compromised, advance to escalation
            self.phase = 3
            logger.info(f"\nRED AGENT [Phase 2 - LATERAL MOVEMENT]: All reachable hosts compromised!")
            logger.info(f"   Compromised: {self.compromised}")
            logger.info(f"   RED AGENT: Advancing to Phase 3 (Escalation)")
            return self._phase_escalation()

        # Pick a random reachable target
        source, target = random.choice(list(reachable_targets))

        logger.info(f"\nRED AGENT [Phase 2 - LATERAL MOVEMENT]: Pivoting {source} -> {target}...")

        # First scan, then exploit
        target_ip = HOST_IPS.get(target, "unknown")
        scan_ok, scan_msg = self._scan(source, target_ip)
        logger.info(f"   Scan: {scan_msg}")

        success, exploit_msg = self._exploit(target)
        self._log_attack("exploit", source, target, exploit_msg)

        if success:
            logger.info(f"   LATERAL MOVEMENT SUCCESS: {target} compromised via {source}")
        else:
            logger.info(f"   LATERAL MOVEMENT FAILED: {exploit_msg}")

        # Check if all targets are now compromised
        all_compromised = all(t in self.compromised for t in self.targets)
        if all_compromised:
            self.phase = 3
            logger.info(f"   RED AGENT: Full network compromise! Advancing to Phase 3 (Escalation)")

        return target

    def _phase_escalation(self):
        """Phase 3: Deepen access - backdoors, persistence, exfiltration."""
        if not self.compromised:
            # Lost all access, fall back
            self.phase = 1
            logger.info(f"\nRED AGENT [Phase 3 - ESCALATION]: No compromised hosts! Falling back to Phase 1")
            return self._phase_initial_access()

        target = random.choice(list(self.compromised))
        attack_type = random.choice(["backdoor", "exfiltrate", "persist"])

        logger.info(f"\nRED AGENT [Phase 3 - ESCALATION]: {attack_type.upper()} on {target}...")

        if attack_type == "backdoor":
            success, msg = self._backdoor(target)
        elif attack_type == "exfiltrate":
            success, msg = self._exfiltrate(target)
        else:
            success, msg = self._persist(target)

        self._log_attack(attack_type, "red_agent", target, msg)

        if success:
            logger.info(f"   ESCALATION SUCCESS: {msg}")
        else:
            logger.info(f"   ESCALATION FAILED: {msg}")

        return target

    def _log_attack(self, attack_type, source, target, detail):
        """Record attack for logging/dashboard."""
        self.attack_log.append({
            "step": self.step_count,
            "phase": self.phase,
            "type": attack_type,
            "source": source,
            "target": target,
            "detail": detail,
        })
