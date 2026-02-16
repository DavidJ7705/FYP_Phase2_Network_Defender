import subprocess
import logging
import random
import time

logger = logging.getLogger(__name__)

CLAB_PREFIX = "clab-fyp-defense-network-"


class RedAgent:
    """
    Scripted Adversary that plants exploits (IOCs) on containers.
    Current Attack: Creating '/tmp/pwned' file.
    """

    def __init__(self, target_list, client=None):
        import docker
        self.client = client or docker.from_env()
        self.targets = target_list
        logger.info(f"🔴 RED AGENT: Initialized. Known targets: {len(self.targets)}")

    def _resolve_container(self, host):
        """Resolve short name to full containerlab container name."""
        full_name = f"{CLAB_PREFIX}{host}"
        return self.client.containers.get(full_name)

    def attack(self, probability=0.5):
        """
        Attempts to compromise a random target with given probability.
        """
        if not self.targets:
            return

        # Random decision: Attack?
        if random.random() > probability:
            return  # No attack this step

        # Pick a target
        target = random.choice(self.targets)
        # Handle prefix
        if not target.startswith("clab-"):
            full_target = f"{CLAB_PREFIX}{target}"
        else:
            full_target = target
        
        logger.info(f"\n🔴 RED AGENT: Initiating attack on {target} ({full_target})...")

        try:
            container = self.client.containers.get(full_target)
            # Simulate exploit: create /tmp/pwned
            # Use /bin/sh absolute path
            exit_code, output = container.exec_run(['/bin/sh', '-c', 'touch /tmp/pwned'])
            
            if exit_code == 0:
                logger.info(f"   🔥 EXPLOIT SUCCESS: {target} is now compromised!")
                return target
            else:
                logger.info(f"   ❌ EXPLOIT FAILED: Return code {exit_code}. Output: {output.decode().strip()}")
                
        except docker.errors.NotFound:
            logger.error(f"   ❌ Attack failed: Container {full_target} not found.")
        except Exception as e:
            logger.error(f"   ❌ Attack script error: {e}")
            
        return None
