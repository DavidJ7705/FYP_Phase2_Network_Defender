from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
import json
import torch

# Collect network state (or load from file if containers aren't running)
try:
    monitor = ContainerlabMonitor()
    state = monitor.get_network_state()
    if not state["containers"]:
        raise RuntimeError("No containers found")
    print(f"Collected live state: {len(state['containers'])} containers")
except Exception as e:
    print(f"Live collection failed ({e}), loading from example_state.json")
    with open("example_state.json", "r") as f:
        state = json.load(f)
    print(f"Loaded saved state: {len(state['containers'])} containers")

# Build graph
builder = ObservationGraphBuilder()
graph = builder.build_graph(state)

print(f"\nGraph built successfully!")
print(f"  Nodes: {graph.x.shape[0]}")
print(f"  Node features: {graph.x.shape[1]} dims")
print(f"  Edges: {graph.edge_index.shape[1]}")
print(f"  Node types: {graph.node_type.shape}")

# Breakdown by type
type_names = {0: "SystemNode", 1: "ConnectionNode", 2: "FileNode", 3: "InternetNode"}
for type_id, type_name in type_names.items():
    count = (graph.node_type == type_id).sum().item()
    if count > 0:
        print(f"    {type_name}: {count}")

# Show edge connectivity
print(f"\n  Edge list:")
for i in range(graph.edge_index.shape[1]):
    src = graph.edge_index[0, i].item()
    dst = graph.edge_index[1, i].item()
    src_type = type_names[graph.node_type[src].item()]
    dst_type = type_names[graph.node_type[dst].item()]
    print(f"    {src} ({src_type}) -> {dst} ({dst_type})")
