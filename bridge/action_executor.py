import docker
import logging
from datetime import datetime

CLAB_PREFIX = "clab-fyp-defense-network-"


class ActionExecutor:
    """Execute agent actions on Containerlab containers."""

    def __init__(self):
        self.client = docker.from_env()
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

    def execute(self, action_type, target_host):
        """
        Execute agent action on target container.

        Args:
            action_type: str - 'Monitor', 'Restore', 'Analyse'
            target_host: str - short container name (e.g. 'web-server')

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
            else:
                return {"success": False, "error": f"Unknown action: {action_type}"}
        except docker.errors.NotFound:
            self.logger.error(f"Container not found: {target_host}")
            return {"success": False, "error": f"Container not found: {target_host}"}
        except Exception as e:
            self.logger.error(f"Action failed: {e}")
            return {"success": False, "error": str(e)}

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
        """Restore action: restart container to clean state."""
        container = self._resolve_container(host)
        container.restart(timeout=10)

        return {
            "success": True,
            "action": "Restore",
            "target": host,
            "message": f"Restarted {host} to clean state",
        }

    def _analyse(self, host):
        """Analyse action: check for suspicious processes/activity."""
        container = self._resolve_container(host)

        ps_result = container.exec_run("ps aux")
        processes = ps_result.output.decode()

        suspicious_patterns = [
            "nc ", "ncat", "netcat",        # Network tools
            "meterpreter", "msf",           # Metasploit
            "reverse", "shell",             # Reverse shells
            "/tmp/", ".sh",                 # Suspicious scripts
            "python -c", "perl -e",         # Inline scripts
            "base64",                       # Encoded payloads
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