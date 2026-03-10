import docker
import json
from datetime import datetime

CLAB_PREFIX = "clab-cage4-defense-network-"


class ActionExecutor:
    def __init__(self):
        self.client = docker.from_env()