from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.Wrappers.EnterpriseMAE import EnterpriseMAE
from CybORG.Agents import SleepAgent

# Initialize the environment
sg = EnterpriseScenarioGenerator()
cyborg = CybORG(sg, 'sim')
env = EnterpriseMAE(env=cyborg)

# Create simple agents (5 blue agents in CC4)
agents = {f'blue_agent_{i}': SleepAgent() for i in range(5)}

# Run a simple episode
reset_result = env.reset()

# Handle the reset return value (could be tuple or dict)
if isinstance(reset_result, tuple):
    observations, info = reset_result
else:
    observations = reset_result

done = False
total_reward = 0
step = 0

print("Starting episode...")
print(f"Agent names: {list(env.agents)}")  # Use env.agents instead

while not done and step < 100:
    # Get actions from all agents
    actions = {}
    for agent_name in env.agents:
        # Use the correct agent from our dict
        agent = agents[agent_name]
        action = agent.get_action(observations[agent_name], env.action_space(agent_name))
        actions[agent_name] = action
    
    # Take a step in the environment
    step_result = env.step(actions)
    
    # Handle different return formats
    if len(step_result) == 5:
        observations, rewards, dones, truncated, infos = step_result
    else:
        observations, rewards, dones, infos = step_result
    
    total_reward += sum(rewards.values())
    done = all(dones.values())
    step += 1
    
    if step % 10 == 0:
        print(f"Step {step}, Total Reward: {total_reward:.2f}")

print(f"\nEpisode finished after {step} steps")
print(f"Final total reward: {total_reward:.2f}")