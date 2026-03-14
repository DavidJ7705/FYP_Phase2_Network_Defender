import docker
import json
from datetime import datetime

CLAB_PREFIX = "clab-cage4-defense-network-"


class ActionExecutor:
    def __init__(self):
        self.client = docker.from_env()

    def execute(self, action, servers, users):
        print(f"Executing action: {action}")
        if action == "analyse":
            return self._analyse(servers, users)
        elif action == "block":
            return self._block(servers, users)
        elif action == "restore":
            return self._restore(servers, users)
        elif action == "unblock":
            return self._unblock(servers, users)
        else:
            raise ValueError(f"Unknown action: {action}")
        