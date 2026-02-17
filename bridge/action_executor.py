import docker
import json
import logging
import random
from datetime import datetime
from pathlib import Path

CLAB_PREFIX = "clab-cage4-defense-network-"

# State file for tracking blocked zones and deployed decoys
STATE_FILE = Path(__file__).parent / "action_state.json"


def _load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"blocked_zones": [], "deployed_decoys": []}


def _save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


class ActionExecutor:
    """Execute agent actions on Containerlab containers."""

    def __init__(self, client=None):
        self.client = client or docker.from_env()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        )

    def _resolve_container(self, host):
        """Resolve short name to full containerlab container name."""
        full_name = f"{CLAB_PREFIX}{host}"
        return self.client.containers.get(full_name)

    def execute(self, action_type, target_host, interface=None):
        """
        Execute agent action on target container.

        Args:
            action_type: str - action name
            target_host: str - short container name (e.g. 'web-server')
            interface: str - network interface (only for BlockTraffic/AllowTraffic)

        Returns:
            dict with action result
        """
        self.logger.info(f"Executing {action_type} on {target_host}")

        try:
            if action_type == "Monitor":
                return self._monitor(target_host)
            elif action_type == "Restore":
                return self._restore(target_host)
            elif action_type == "Analyse":
                return self._analyse(target_host)
            elif action_type == "Remove":
                return self._remove(target_host)
            elif action_type == "DeployDecoy":
                return self._deploy_decoy(target_host)
            elif action_type == "BlockTrafficZone":
                return self._block_traffic_zone(target_host, interface or "eth1")
            elif action_type == "AllowTrafficZone":
                return self._allow_traffic_zone(target_host, interface or "eth1")
            else:
                return {"success": False, "error": f"Unknown action: {action_type}"}
        except docker.errors.NotFound:
            self.logger.error(f"Container not found: {target_host}")
            return {"success": False, "error": f"Container not found: {target_host}"}
        except Exception as e:
            self.logger.error(f"Action failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Existing actions ─────────────────────────────────────────

    def _monitor(self, host):
        """Monitor action: capture network traffic with tcpdump."""
        container = self._resolve_container(host)

        try:
            container.exec_run(
                "tcpdump -i eth1 -w /tmp/capture.pcap -c 100",
                detach=True,
            )
            return {
                "success": True,
                "action": "Monitor",
                "target": host,
                "message": f"Started network monitoring on {host}",
            }
        except Exception as e:
            return {
                "success": True,
                "action": "Monitor",
                "target": host,
                "message": f"Monitoring requested for {host} (tcpdump not available: {e})",
            }

    def _restore(self, host):
        """Restore action: restart container AND clean specific IOCs."""
        self.logger.info(f"Restoring {host}...")
        container = self._resolve_container(host)

        # 1. Clean the IOC
        try:
            container.exec_run(['/bin/sh', '-c', 'rm -f /tmp/pwned'])
        except Exception as e:
            self.logger.warning(f"Failed to clean IOC on {host}: {e}")

        # 2. Clear any blocked zones on this host (restart wipes iptables anyway)
        state = _load_state()
        state["blocked_zones"] = [
            b for b in state["blocked_zones"] if b["container"] != host
        ]
        state["deployed_decoys"] = [
            d for d in state["deployed_decoys"] if d["container"] != host
        ]
        _save_state(state)

        # 3. Restart to kill any in-memory malware/processes
        container.restart(timeout=10)

        return {
            "success": True,
            "action": "Restore",
            "target": host,
            "message": f"Restored {host} (Cleaned + Restarted)",
        }

    def _analyse(self, host):
        """Analyse action: check for suspicious processes/activity."""
        container = self._resolve_container(host)

        ps_result = container.exec_run("ps aux")
        processes = ps_result.output.decode()

        suspicious_patterns = [
            "nc ", "ncat", "netcat",
            "meterpreter", "msf",
            "reverse", "shell",
            "/tmp/", ".sh",
            "python -c", "perl -e",
            "base64",
        ]

        suspicious_found = []
        for pattern in suspicious_patterns:
            if pattern in processes.lower():
                suspicious_found.append(pattern)

        is_suspicious = len(suspicious_found) > 0

        return {
            "success": True,
            "action": "Analyse",
            "target": host,
            "suspicious": is_suspicious,
            "patterns_found": suspicious_found,
            "process_count": len(processes.strip().split("\n")) - 1,
            "message": f"Analysis complete: {'SUSPICIOUS' if is_suspicious else 'CLEAN'}",
        }

    # ── New actions ──────────────────────────────────────────────

    def _remove(self, host):
        """Remove action: kill suspicious processes + clean IOCs WITHOUT restart."""
        self.logger.info(f"Removing malicious artifacts from {host}...")
        container = self._resolve_container(host)
        cleaned = []

        # 1. Remove the IOC file
        try:
            container.exec_run(['/bin/sh', '-c', 'rm -f /tmp/pwned'])
            cleaned.append("IOC file")
        except Exception:
            pass

        # 2. Kill suspicious processes
        try:
            ps_result = container.exec_run("ps aux")
            processes = ps_result.output.decode()

            suspicious_patterns = ["nc ", "ncat", "netcat", "meterpreter", "reverse"]

            for line in processes.split("\n")[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                pid = parts[1]
                cmd = " ".join(parts[10:]) if len(parts) > 10 else line
                for pattern in suspicious_patterns:
                    if pattern.lower() in cmd.lower():
                        container.exec_run(f"kill -9 {pid}")
                        cleaned.append(f"PID {pid} ({pattern.strip()})")
                        break
        except Exception as e:
            self.logger.warning(f"Process cleanup failed on {host}: {e}")

        return {
            "success": True,
            "action": "Remove",
            "target": host,
            "cleaned": cleaned,
            "message": f"Removed {len(cleaned)} artifacts from {host} (no restart)",
        }

    def _deploy_decoy(self, host):
        """DeployDecoy action: start a netcat honeypot listener."""
        self.logger.info(f"Deploying decoy on {host}...")
        container = self._resolve_container(host)

        port = random.randint(8000, 9999)

        try:
            # busybox nc: -l = listen, -p = port
            # Run in background, log connections
            cmd = f"nc -l -p {port} > /tmp/decoy_{port}.log 2>&1 & echo $!"
            result = container.exec_run(['/bin/sh', '-c', cmd])

            if result.exit_code == 0:
                pid = result.output.decode().strip()

                state = _load_state()
                state["deployed_decoys"].append({
                    "container": host,
                    "port": port,
                    "pid": pid,
                    "timestamp": datetime.now().isoformat(),
                })
                _save_state(state)

                return {
                    "success": True,
                    "action": "DeployDecoy",
                    "target": host,
                    "port": port,
                    "message": f"Deployed decoy honeypot on {host}:{port}",
                }
            else:
                return {
                    "success": False,
                    "action": "DeployDecoy",
                    "target": host,
                    "error": f"nc failed: {result.output.decode()}",
                }
        except Exception as e:
            return {
                "success": False,
                "action": "DeployDecoy",
                "target": host,
                "error": str(e),
            }

    def _block_traffic_zone(self, host, interface):
        """BlockTrafficZone: drop incoming traffic on a specific interface."""
        self.logger.info(f"Blocking traffic on {host}:{interface}...")
        container = self._resolve_container(host)
        rule_id = f"CYBORG_BLOCK_{interface}"

        # Check if already blocked
        state = _load_state()
        for b in state["blocked_zones"]:
            if b["container"] == host and b["interface"] == interface:
                return {
                    "success": True,
                    "action": "BlockTrafficZone",
                    "target": host,
                    "message": f"Traffic already blocked on {host}:{interface}",
                }

        # Try iptables first
        method = "iptables"
        check = container.exec_run("which iptables")
        if check.exit_code != 0:
            # Try installing
            container.exec_run("apk add --no-cache iptables 2>/dev/null")
            check = container.exec_run("which iptables")

        if check.exit_code == 0:
            cmd = f"iptables -A INPUT -i {interface} -j DROP -m comment --comment {rule_id}"
            result = container.exec_run(['/bin/sh', '-c', cmd])
            if result.exit_code != 0:
                # iptables failed (maybe no module), fall back
                method = None
        else:
            method = None

        # Fallback: disable the interface entirely
        if method is None:
            method = "ip_link_down"
            result = container.exec_run(f"ip link set {interface} down")
            if result.exit_code != 0:
                return {
                    "success": False,
                    "action": "BlockTrafficZone",
                    "target": host,
                    "error": f"Both iptables and ip link failed on {host}:{interface}",
                }

        state["blocked_zones"].append({
            "container": host,
            "interface": interface,
            "method": method,
            "rule_id": rule_id,
            "timestamp": datetime.now().isoformat(),
        })
        _save_state(state)

        return {
            "success": True,
            "action": "BlockTrafficZone",
            "target": host,
            "interface": interface,
            "method": method,
            "message": f"Blocked traffic on {host}:{interface} ({method})",
        }

    def _allow_traffic_zone(self, host, interface):
        """AllowTrafficZone: reverse a previous block on an interface."""
        self.logger.info(f"Allowing traffic on {host}:{interface}...")
        container = self._resolve_container(host)
        rule_id = f"CYBORG_BLOCK_{interface}"

        state = _load_state()
        blocked = None
        remaining = []
        for b in state["blocked_zones"]:
            if b["container"] == host and b["interface"] == interface and blocked is None:
                blocked = b
            else:
                remaining.append(b)

        if blocked is None:
            return {
                "success": True,
                "action": "AllowTrafficZone",
                "target": host,
                "message": f"Traffic already allowed on {host}:{interface} (no block found)",
            }

        if blocked["method"] == "iptables":
            cmd = f"iptables -D INPUT -i {interface} -j DROP -m comment --comment {rule_id}"
            container.exec_run(['/bin/sh', '-c', cmd])
        else:
            container.exec_run(f"ip link set {interface} up")

        state["blocked_zones"] = remaining
        _save_state(state)

        return {
            "success": True,
            "action": "AllowTrafficZone",
            "target": host,
            "interface": interface,
            "message": f"Allowed traffic on {host}:{interface}",
        }
