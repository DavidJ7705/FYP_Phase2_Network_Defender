import torch
import os

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)

data = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=False)
args, kwargs = data["agent"]

print(f"Agent constructor args: {args}")
print(f"Agent constructor kwargs: {list(kwargs.keys())}")
print(f"\ninput_dimension = {args[0]}")
