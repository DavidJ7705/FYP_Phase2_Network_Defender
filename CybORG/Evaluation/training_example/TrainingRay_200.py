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
        steps=200,  # Reduced to 200 steps - more manageable
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
    .debugging(logger_config={"logdir":"logs/DQN_200steps", "type":"ray.tune.logger.TBXLogger"})
    .environment(env="CC4")
    .api_stack(enable_rl_module_and_learner=False, enable_env_runner_and_connector_v2=False)
    # Collect experience with multiple workers
    .env_runners(
        num_env_runners=4,
        num_envs_per_env_runner=1,
        rollout_fragment_length=200,  # Match 200-step episodes
    )
    # Training configuration - more conservative
    .training(
        replay_buffer_config={
            'type': 'MultiAgentPrioritizedReplayBuffer',
            'capacity': 100000,
        },
        train_batch_size=512,  # Smaller batch for stability
        lr=0.0001,  # Lower learning rate
        gamma=0.95,  # Medium-term planning (not too long)
        target_network_update_freq=1000,
        num_steps_sampled_before_learning_starts=2000,
        double_q=True,
        dueling=True,
        n_step=1,  # Single-step returns for simpler learning
    )
    # Evaluation configuration
    .evaluation(
        evaluation_interval=25,
        evaluation_duration=10,
        evaluation_num_env_runners=1,
        evaluation_config={
            "explore": False,
        }
    )
    # Resources
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

# Build the algorithm
print(f"\n{'='*60}")
print("Initializing DQN Algorithm for 200-step episodes")
print(f"{'='*60}\n")

algo = DQN(config=algo_config)

# Training loop with better monitoring
num_iterations = 500
best_reward = float('-inf')
worst_reward = float('inf')
no_improvement_count = 0
patience = 100
improvement_threshold = 50.0  # Adjusted for 200-step episodes

print(f"\n{'='*60}")
print(f"Starting training for up to {num_iterations} iterations")
print(f"Episode length: 200 steps")
print(f"Early stopping patience: {patience} iterations")
print(f"Improvement threshold: {improvement_threshold}")
print(f"{'='*60}\n")

training_start_time = time.time()
rewards_history = []

for i in range(num_iterations):
    try:
        iteration_start = time.time()
        train_info = algo.train()
        iteration_time = time.time() - iteration_start
        
        # Extract metrics
        env_runner_info = train_info.get('env_runners', {})
        reward_mean = env_runner_info.get('episode_reward_mean', None)
        episode_len = env_runner_info.get('episode_len_mean', None)
        num_episodes = env_runner_info.get('num_episodes', 0)
        timesteps = train_info.get('num_env_steps_sampled_this_iter', 0)
        
        # Print progress
        print(f"\n[Iteration {i+1}/{num_iterations}] (Time: {iteration_time:.1f}s)")
        print(f"  Episodes: {num_episodes} | Timesteps: {timesteps}")
        
        if reward_mean is not None and not np.isnan(reward_mean):
            rewards_history.append(reward_mean)
            print(f"  Mean reward: {reward_mean:.2f}")
            print(f"  Episode length: {episode_len:.2f}" if episode_len else "")
            
            # Track best AND worst to see if we're degrading
            if reward_mean < worst_reward:
                worst_reward = reward_mean
                print(f"  ⚠️  New WORST reward: {worst_reward:.2f}")
            
            # Track best performance
            if reward_mean > best_reward + improvement_threshold:
                improvement = reward_mean - best_reward
                best_reward = reward_mean
                no_improvement_count = 0
                
                best_save = os.path.abspath("experiment_200steps_best")
                algo.save(best_save)
                print(f"  ⭐ NEW BEST! Improved by {improvement:.2f} (Total: {best_reward:.2f})")
            else:
                no_improvement_count += 1
                if no_improvement_count <= 10 or no_improvement_count % 25 == 0:
                    print(f"  No improvement ({no_improvement_count}/{patience})")
            
            # Show trend over last 10 iterations
            if len(rewards_history) >= 10:
                recent_avg = mean(rewards_history[-10:])
                older_avg = mean(rewards_history[-20:-10]) if len(rewards_history) >= 20 else rewards_history[0]
                trend = "↑ improving" if recent_avg > older_avg else "↓ degrading"
                print(f"  Trend (last 10): {recent_avg:.1f} vs previous 10: {older_avg:.1f} {trend}")
            
            # Early stopping
            if no_improvement_count >= patience:
                print(f"\n{'='*60}")
                print(f"EARLY STOPPING: No improvement for {patience} iterations")
                print(f"Best reward: {best_reward:.2f}")
                print(f"{'='*60}\n")
                break
        else:
            print(f"  ⚠️  No episode data yet")
        
        # Periodic checkpoints
        if (i + 1) % 50 == 0:
            interim_save = os.path.abspath(f"experiment_200steps_iter_{i+1}")
            algo.save(interim_save)
            elapsed = time.time() - training_start_time
            print(f"  💾 Checkpoint saved (Elapsed: {elapsed/60:.1f} min)")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted!")
        user_save = input("Save current progress? (y/n): ")
        if user_save.lower() == 'y':
            interrupt_save = os.path.abspath("experiment_200steps_interrupted")
            algo.save(interrupt_save)
            print(f"✓ Saved to: {interrupt_save}")
        break
    except Exception as e:
        print(f"\n✗ Error at iteration {i+1}: {e}")
        import traceback
        traceback.print_exc()
        continue

# Training complete
total_time = time.time() - training_start_time

print(f"\n{'='*60}")
print("TRAINING COMPLETE")
save_path = os.path.abspath("experiment_200steps_final")
algo.save(save_path)
print(f"✓ Saved to: {save_path}")
print(f"Total time: {total_time/60:.1f} minutes")

# Final evaluation
print(f"\n{'='*60}")
print("Final Evaluation")
print(f"{'='*60}\n")

try:
    output = algo.evaluate()
    
    if 'evaluation' in output:
        eval_results = output['evaluation']
        
        print(f"Avg episode length: {eval_results.get('episode_len_mean', 'N/A'):.1f}")
        print(f"Avg episode reward: {eval_results.get('episode_reward_mean', 'N/A'):.1f}")
        print(f"Best episode reward: {eval_results.get('episode_reward_max', 'N/A'):.1f}")
        print(f"Worst episode reward: {eval_results.get('episode_reward_min', 'N/A'):.1f}")
        
        if 'policy_reward_mean' in eval_results:
            print("\nPer-Agent Performance:")
            for agent, reward in eval_results['policy_reward_mean'].items():
                print(f"  {agent}: {reward:.2f}")
    else:
        print("No evaluation data")
        
except Exception as e:
    print(f"Evaluation failed: {e}")

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"Best reward: {best_reward:.2f}")
print(f"Worst reward: {worst_reward:.2f}")
print(f"Iterations: {i+1}")
print(f"Training time: {total_time/60:.1f} minutes")
print(f"{'='*60}\n")