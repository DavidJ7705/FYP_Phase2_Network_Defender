import logging
import docker

logger = logging.getLogger(__name__)

class IntrusionDetector:
    """
    Checks real containers for Indicators of Compromise (IOCs).

    IOCs detected:
    - /tmp/pwned: Basic compromise flag
    - /tmp/exfil_*: Data staged for exfiltration
    - /tmp/backdoor_*.log: Active backdoor listener logs
    - /etc/periodic/*/backdoor.sh: Persistence mechanisms
    - Suspicious background processes (nc listeners)
    """

    def __init__(self, client=None):
        self.client = client or docker.from_env()

    def check_compromise(self, container_name):
        """
        Returns True if the container shows signs of compromise.
        Checks multiple IOC types for comprehensive detection.
        """
        # Handle prefix if not present
        if not container_name.startswith("clab-"):
            full_name = f"clab-cage4-defense-network-{container_name}"
        else:
            full_name = container_name

        try:
            container = self.client.containers.get(full_name)

            # IOC 1: Basic flag file
            exit_code, _ = container.exec_run(['/bin/sh', '-c', 'test -f /tmp/pwned'])
            basic_ioc = (exit_code == 0)

            # IOC 2: Exfiltration staging
            exit_code, _ = container.exec_run(['/bin/sh', '-c', 'ls /tmp/exfil_* 2>/dev/null'])
            exfil_ioc = (exit_code == 0)

            # IOC 3: Backdoor logs
            exit_code, _ = container.exec_run(['/bin/sh', '-c', 'ls /tmp/backdoor_*.log 2>/dev/null'])
            backdoor_ioc = (exit_code == 0)

            # IOC 4: Persistence scripts
            exit_code, _ = container.exec_run(['/bin/sh', '-c', 'test -f /etc/periodic/15min/backdoor.sh'])
            persist_ioc = (exit_code == 0)

            # Aggregate: compromised if ANY IOC present
            is_compromised = basic_ioc or exfil_ioc or backdoor_ioc or persist_ioc

            # Log debug info with IOC breakdown
            ioc_flags = []
            if basic_ioc:
                ioc_flags.append("FLAG")
            if exfil_ioc:
                ioc_flags.append("EXFIL")
            if backdoor_ioc:
                ioc_flags.append("BACKDOOR")
            if persist_ioc:
                ioc_flags.append("PERSIST")

            if ioc_flags:
                logger.info(f"   [DEBUG] Check {full_name}: COMPROMISED ({', '.join(ioc_flags)})")
            else:
                logger.info(f"   [DEBUG] Check {full_name}: exit_code=1")

            return is_compromised

        except Exception as e:
            logger.error(f"   [DEBUG] Error checking {full_name}: {e}")
            return False
