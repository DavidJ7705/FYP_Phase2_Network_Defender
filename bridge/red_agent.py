import subprocess
import logging
import random
import time

logger = logging.getLogger(__name__)

class RedAgent:
    """
    Scripted Adversary that plants exploits (IOCs) on containers.
    Current Attack: Creating '/tmp/pwned' file.
    """
    
    def __init__(self, target_list):
        self.targets = target_list
        logger.info(f"🔴 RED AGENT: Initialized. Known targets: {len(self.targets)}")

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
            full_target = f"clab-fyp-defense-network-{target}"
        else:
            full_target = target

        # Resolve container via docker client
        import docker
        client = docker.from_env()
        
        logger.info(f"\n🔴 RED AGENT: Initiating attack on {target} ({full_target})...")
        
        try:
            container = client.containers.get(full_target)
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
