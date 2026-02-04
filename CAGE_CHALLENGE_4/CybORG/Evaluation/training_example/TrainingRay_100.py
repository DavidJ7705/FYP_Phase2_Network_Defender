import sys
import os
import inspect
import time

from statistics import mean, stdev
from typing import Any
from rich import print

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from CybORG import CybORG
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.Wrappers import BaseWrapper, BlueFlatWrapper, BlueFixedActionWrapper, EnterpriseMAE

import numpy as np

from ray.rllib.env import MultiAgentEnv
from ray.rllib.algorithms.ppo import PPOConfig, PPO
from ray.rllib.algorithms.dqn import DQNConfig, DQN
from ray.rllib.policy.policy import PolicySpec

from ray.tune import register_env

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)


def env_creator_CC4(env_config: dict):
    sg = EnterpriseScenarioGenerator(
        blue_agent_class=SleepAgent,
        green_agent_class=EnterpriseGreenAgent,
        red_agent_class=FiniteStateRedAgent,
        #red_agent_class=SleepAgent,
        steps=100,
    )
    cyborg = CybORG(scenario_generator=sg)
    cyborg = EnterpriseMAE(cyborg)
    return cyborg


NUM_AGENTS = 5
POLICY_MAP = {f"blue_agent_{i}": f"Agent{i}" for i in range(NUM_AGENTS)}


def policy_mapper(agent_id, episode, worker, **kwargs):
    return POLICY_MAP[agent_id]


register_env(name="CC4", env_creator=lambda config: env_creator_CC4(config))
env = env_creator_CC4({})


algo_config = (
    DQNConfig().framework("torch")
    .debugging(logger_config={"logdir":"logs/DQN_Complicated_SleepRed", "type":"ray.tune.logger.TBXLogger"})
    .environment(env="CC4")
    .api_stack(enable_rl_module_and_learner=False, enable_env_runner_and_connector_v2=False)
    .training(replay_buffer_config={'type': 'MultiAgentPrioritizedReplayBuffer'})
    .multi_agent(
        policies={
            ray_agent: PolicySpec(
                policy_class=None,
                observation_space=env.observation_space(cyborg_agent),
                action_space=env.action_space(cyborg_agent),
                config={"gamma": 0.85},
            )
            for cyborg_agent, ray_agent in POLICY_MAP.items()
        },
        policy_mapping_fn=policy_mapper,
    )
)

# Load the previously trained agent with FULL path
algo = DQN(config=algo_config)
checkpoint_path = os.path.abspath("experiment1a")
print(f"Loading checkpoint from: {checkpoint_path}")
algo.restore(checkpoint_path)

# Continue training for 100 more iterations
for i in range(100):
    train_info = algo.train()
    print(f"Training iteration {i+1}/100 completed")

# Save with full path
save_path = os.path.abspath("experiment1a_100more")
algo.save(save_path)
print(f"Saved checkpoint to: {save_path}")

output = algo.evaluate()

print(output)
print(
    "Avg episode length for trained agent: %.1f"
    % output["evaluation"]["episode_len_mean"]
)