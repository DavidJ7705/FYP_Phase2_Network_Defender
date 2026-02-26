import torch
import os, sys
from graph_builder import FEATURE_DIM, NUM_ROUTERS, ObservationGraphBuilder

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)



data = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=False)
in_dim = data["agent"][0][0]

print(f"Dimension check")
print(f"Agent in_dim (from weights):{in_dim}")
print(f"FEATURE_DIM (graph builder):{FEATURE_DIM}")
print(f"Match: {in_dim == FEATURE_DIM}")

builder = ObservationGraphBuilder()
print(f"\nObservationGraphBuilder instantiated ok i think")
