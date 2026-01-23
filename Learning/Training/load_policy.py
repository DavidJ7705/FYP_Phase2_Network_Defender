# mac: venv/bin/python -m Learning.Training.load_policy
# windows: .\venv\Scripts\python -m Learning.Training.load_policy

import torch
import pickle
from ray.rllib.algorithms.ppo import PPO  # <-- correct import in Ray 2.x

# Path to the saved policy
policy_path = "results/policies/Agent0/policy_state.pkl"

# Load the state dictionary
with open(policy_path, "rb") as f:
    policy_state = pickle.load(f)

# Inspect the keys (weights & buffers)
print(policy_state.keys())
