from network_monitor import ContainerlabMonitor
from intrusion_detector import IntrusionDetector
from graph_builder import CONTAINER_ROLES, ObservationGraphBuilder

monitor = ContainerlabMonitor()
state = monitor.get_network_state()
builder = ObservationGraphBuilder()
detector = IntrusionDetector()


servers, users, routers = builder.classify_node_type(state)

results = detector.scan(servers + users)
for host, level in results.items():
    if level > 0:
        print(f"Host {host} is compromised at level {level}.")
print("Scan complete.")
