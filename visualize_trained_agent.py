import numpy as np
from ray.rllib.algorithms.dqn import DQN
from ray.tune import register_env

from CybORG import CybORG
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.Wrappers import EnterpriseMAE
from CybORG.render.visualisation.VisualiseRedExpansion import VisualiseRedExpansion

# Custom agent wrapper to use trained Ray agent
class TrainedRayAgent:
    def __init__(self, algo, agent_id):
        self.algo = algo
        self.agent_id = agent_id
        
    def get_action(self, observation, action_space):
        # Get action from trained Ray agent
        action = self.algo.compute_single_action(observation, policy_id=f"Agent{self.agent_id}")
        return action

def env_creator_CC4(env_config: dict):
    sg = EnterpriseScenarioGenerator(
        blue_agent_class=SleepAgent,  # Will be replaced with trained agents
        green_agent_class=EnterpriseGreenAgent,
        red_agent_class=FiniteStateRedAgent,
        steps=200,
    )
    cyborg = CybORG(scenario_generator=sg)
    cyborg = EnterpriseMAE(cyborg)
    return cyborg

# Register environment
register_env(name="CC4", env_creator=lambda config: env_creator_CC4(config))

# Load trained model
print("Loading trained model...")
algo = DQN.from_checkpoint("experiment1a")

# Create environment for visualization
steps = 200
sg = EnterpriseScenarioGenerator(
    blue_agent_class=SleepAgent,
    green_agent_class=EnterpriseGreenAgent, 
    red_agent_class=FiniteStateRedAgent,
    steps=steps
)
cyborg = CybORG(scenario_generator=sg, seed=7629)

# Reset environment
obs = cyborg.reset()
print("Environment reset. Starting visualization...")

# Create visualization
visualise = VisualiseRedExpansion(cyborg, steps)

# Run episode with trained agents
for i in range(steps):
    print(f"Step {i+1}/{steps}")
    
    # Get actions from trained agents for each blue agent
    actions = {}
    for agent_id in obs.keys():
        if 'blue_agent' in agent_id:
            # Extract agent number from agent_id (e.g., 'blue_agent_0' -> 0)
            agent_num = int(agent_id.split('_')[-1])
            policy_id = f"Agent{agent_num}"
            
            # Get action from trained model
            action = algo.compute_single_action(obs[agent_id], policy_id=policy_id)
            actions[agent_id] = action
    
    # Step environment
    obs, rewards, dones, infos = cyborg.step(actions)
    
    # Record state for visualization
    visualise.visualise_step()
    
    # Print some info
    if i % 50 == 0:
        total_reward = sum(rewards.values()) if rewards else 0
        print(f"  Total reward: {total_reward:.2f}")

print("Episode finished. Generating visualization...")

# Show the visualization
visualise.show_graph()
print("Visualization complete! Check the generated graph.")