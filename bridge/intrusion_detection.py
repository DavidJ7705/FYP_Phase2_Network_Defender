import logging
import docker

logger = logging.getLogger(__name__)

class IntrusionDetector:
    """
    Checks real containers for Indicators of Compromise (IOCs).
    Current IOC: Presence of '/tmp/pwned' file.
    """
    
    def __init__(self):
        self.client = docker.from_env()

    def check_compromise(self, container_name):
        """
        Returns True if the container shows signs of compromise.
        """
        # Handle prefix if not present
        if not container_name.startswith("clab-"):
            full_name = f"clab-fyp-defense-network-{container_name}"
        else:
            full_name = container_name
            
        try:
            container = self.client.containers.get(full_name)
            
            # Check for the flag file using 'test -f'
            # exec_run returns (exit_code, output)
            # Use /bin/sh to ensure shell builtin/path resolution
            exit_code, _ = container.exec_run(['/bin/sh', '-c', 'test -f /tmp/pwned'])
            
            # Log debug info
            logger.info(f"   [DEBUG] Check {full_name}: exit_code={exit_code}")
            
            # exit code 0 = file exists (Compromised)
            # exit code 1 = file missing (Clean)
            return exit_code == 0
            
        except Exception as e:
            logger.error(f"   [DEBUG] Error checking {full_name}: {e}")
            return False
