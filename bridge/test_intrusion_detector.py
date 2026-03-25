import docker
from network_monitor import ContainerlabMonitor
from intrusion_detector import IntrusionDetector
from graph_builder import CONTAINER_ROLES, ObservationGraphBuilder

monitor = ContainerlabMonitor()
state = monitor.get_network_state()
builder = ObservationGraphBuilder()
detector = IntrusionDetector()
client = docker.from_env()


PREFIX = "clab-cage4-defense-network-"

servers, users, routers = builder.classify_node_type(state)
target = servers[0]["clean_name"]  #pick the first server for testing
full = PREFIX + target

print(f"Scanning {full}\n")

print("Clean")
results = detector.scan(servers + users)
print(f"{target}:level={results[target]}.")
assert results[target] == 0

print("\nPlanting user marker")
client.containers.get(full).exec_run("touch /tmp/.compromised")

print("\scan user marker")
results = detector.scan(servers + users)
print(f"{target}:level={results[target]}.")
assert results[target] == 1


print("\nPlanting root marker")
client.containers.get(full).exec_run("touch /root/.compromised")

print("\scan root marker")
results = detector.scan(servers + users)
print(f"{target}:level={results[target]}.")
assert results[target] == 2



print("\nCleaning up ")
client.containers.get(full).exec_run("rm -f /tmp/.compromised && rm -f /root/.compromised")

print("\scan clean")
results = detector.scan(servers + users)
print(f"{target}:level={results[target]}.")
assert results[target] == 0

print("\nall tests good")
