from network_monitor import ContainerlabMonitor
import json

monitor = ContainerlabMonitor()
state = monitor.get_network_state()

print(f"Timestamp: {state['timestamp']}")
print(f"Containers: {len(state['containers'])}")
for c in state["containers"]:
    print(f"  - {c['name']}: {c['ip']} ({c['status']}) [{c['image']}]")

print(f"\nProcesses collected from {len(state['processes'])} containers:")
for name, procs in state["processes"].items():
    if isinstance(procs, list):
        print(f"  - {name}: {len(procs)} processes")
    else:
        print(f"  - {name}: {procs}")

print(f"\nConnections collected from {len(state['connections'])} containers:")
for name, ports in state["connections"].items():
    if isinstance(ports, list):
        print(f"  - {name}: ports {ports}" if ports else f"  - {name}: no open ports")
    else:
        print(f"  - {name}: {ports}")

# Save example output
with open("example_state.json", "w") as f:
    json.dump(state, f, indent=2)

print("\nExample state saved to example_state.json")
