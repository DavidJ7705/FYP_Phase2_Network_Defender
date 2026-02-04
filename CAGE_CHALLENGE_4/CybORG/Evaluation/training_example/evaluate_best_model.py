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
        steps=200,
    )
    cyborg = CybORG(scenario_generator=sg, seed=42)  # Seed goes here instead!
    cyborg = EnterpriseMAE(cyborg)
    return cyborg


NUM_AGENTS = 5
POLICY_MAP = {f"blue_agent_{i}": f"Agent{i}" for i in range(NUM_AGENTS)}


def policy_mapper(agent_id, episode, worker, **kwargs):
    return POLICY_MAP[agent_id]


register_env(name="CC4", env_creator=lambda config: env_creator_CC4(config))
env = env_creator_CC4({})

print(f"\n{'='*60}")
print("Loading BEST Trained Model")
print(f"{'='*60}\n")

# Configuration (must match training configuration)
algo_config = (
    DQNConfig().framework("torch")
    .environment(env="CC4")
    .api_stack(enable_rl_module_and_learner=False, enable_env_runner_and_connector_v2=False)
    .env_runners(
        num_env_runners=1,  # Just need 1 for inference
        num_envs_per_env_runner=1,
        rollout_fragment_length=200,
    )
    .training(
        replay_buffer_config={
            'type': 'MultiAgentPrioritizedReplayBuffer',
            'capacity': 100000,
        },
        train_batch_size=512,
        lr=0.0001,
        gamma=0.95,
        target_network_update_freq=1000,
        num_steps_sampled_before_learning_starts=2000,
        double_q=True,
        dueling=True,
        n_step=1,
    )
    .resources(
        num_gpus=0,
    )
    .multi_agent(
        policies={
            ray_agent: PolicySpec(
                policy_class=None,
                observation_space=env.observation_space(cyborg_agent),
                action_space=env.action_space(cyborg_agent),
                config={"gamma": 0.95},
            )
            for cyborg_agent, ray_agent in POLICY_MAP.items()
        },
        policy_mapping_fn=policy_mapper,
    )
)

# Create algorithm and load the BEST checkpoint
algo = DQN(config=algo_config)

# Checkpoint is at project root
checkpoint_path = os.path.join(project_root, "experiment_200steps_best")
print(f"Loading checkpoint from: {checkpoint_path}")

try:
    algo.restore(checkpoint_path)
    print("✓ Successfully loaded BEST model (from iteration 55, reward: -3525.50)")
except Exception as e:
    print(f"✗ Error loading checkpoint: {e}")
    print("Make sure the checkpoint path is correct!")
    print(f"Looking in: {checkpoint_path}")
    print(f"Does it exist? {os.path.exists(checkpoint_path)}")
    sys.exit(1)

print(f"\n{'='*60}")
print("Running Evaluation Episodes")
print(f"{'='*60}\n")

# Run multiple test episodes to see performance
num_test_episodes = 10
episode_rewards = []

for episode in range(num_test_episodes):
    print(f"\nEpisode {episode + 1}/{num_test_episodes}")
    
    # Reset environment
    obs, info = env.reset()
    done = {"__all__": False}
    total_reward = 0
    step = 0
    
    while not done["__all__"] and step < 200:
        # Get actions from trained agents
        actions = {}
        for agent_id in obs.keys():
            policy_id = POLICY_MAP[agent_id]
            action = algo.compute_single_action(
                observation=obs[agent_id],
                policy_id=policy_id,
                explore=False  # No exploration during testing
            )
            actions[agent_id] = action
        
        # Step environment
        obs, rewards, done, truncated, info = env.step(actions)
        
        # Accumulate rewards
        episode_reward = sum(rewards.values())
        total_reward += episode_reward
        step += 1
    
    episode_rewards.append(total_reward)
    print(f"  Total reward: {total_reward:.2f}")
    print(f"  Steps taken: {step}")

print(f"\n{'='*60}")
print("Test Results Summary")
print(f"{'='*60}")
print(f"Episodes run: {num_test_episodes}")
print(f"Average reward: {mean(episode_rewards):.2f}")
print(f"Std deviation: {stdev(episode_rewards):.2f}" if len(episode_rewards) > 1 else "")
print(f"Best episode: {max(episode_rewards):.2f}")
print(f"Worst episode: {min(episode_rewards):.2f}")
print(f"{'='*60}\n")

# Also run official RLlib evaluation
print(f"\n{'='*60}")
print("Running Official RLlib Evaluation")
print(f"{'='*60}\n")

try:
    eval_results = algo.evaluate()
    
    if 'evaluation' in eval_results:
        eval_data = eval_results['evaluation']
        print(f"Avg episode reward: {eval_data.get('episode_reward_mean', 'N/A'):.2f}")
        print(f"Avg episode length: {eval_data.get('episode_len_mean', 'N/A'):.2f}")
        print(f"Max episode reward: {eval_data.get('episode_reward_max', 'N/A'):.2f}")
        print(f"Min episode reward: {eval_data.get('episode_reward_min', 'N/A'):.2f}")
        
        if 'policy_reward_mean' in eval_data:
            print("\nPer-Agent Rewards:")
            for agent, reward in eval_data['policy_reward_mean'].items():
                print(f"  {agent}: {reward:.2f}")
    else:
        print("No evaluation data available")
        
except Exception as e:
    print(f"Evaluation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n✓ Evaluation complete!")