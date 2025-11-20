#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/01_Getting_Started/2_Getting_Started/
# to run: venv/bin/python -m Learning.tutorial_getting_started

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.Wrappers import BlueEnterpriseWrapper, BlueFlatWrapper, BlueFixedActionWrapper
import numpy as np
from rich import print

#Initialize
sg = EnterpriseScenarioGenerator()
cyborg = CybORG(scenario_generator=sg)
env = BlueEnterpriseWrapper(env=cyborg)

#reset environment
obs, _ = env.reset()

print("-"*50)
print("CybORG CAGE Challenge 4 - Getting Started Tutorial")
print("-"*50)

#Viewing Agents
print("All CybORG Agents:")
print(cyborg.active_agents)

print("\nAll Blue Agents in Environment:")
print(list(obs.keys()))


print("-"*50)

#Agent Observations
print("\nBlue Agent 0's Initial Observations (Truncated to 10):")
print(list(obs['blue_agent_0'])[:10], "...")

print("\nBlue Agent 0's Action Space:")
print(env.action_space('blue_agent_0'))
print("\nSome of those actions:")
action_list = env.action_labels('blue_agent_0')
for i, action in enumerate(action_list[:10]):
    print(f"{i}: {action}")


print("-"*50)


print("\nTake an Action:")
obs, _ = env.reset()
actions = {'blue_agent_0' : 42}
obs, reward, terminated, truncated, info = env.step(actions)
print(f"Reward: {reward['blue_agent_0']}")


print("-"*50)

#Sending a Message from 1 Agent
print("\nSend a message:")
env = BlueFixedActionWrapper(env=cyborg)
obs, _ = env.reset()

print("blue_agent_1 initial observations: ",list(obs['blue_agent_1'].keys()))

actions = {'blue_agent_0' : 42}
messages = {'blue_agent_0' : np.array([1,0,0,0,0,1,0,1])}
obs, reward, terminated, truncated, info = env.step(actions, messages=messages)

print("\nCheck did blue_agent_1 receive the message:")
print("Keys: ",list(obs['blue_agent_1'].keys())) #note the keys change after the first env.step

if 'message' in obs['blue_agent_1']:
    print("Message Received by blue_agent_1:")
    print(obs['blue_agent_1']['message'])


print("-"*50)

#Convert Observations Format
print("\nConvert Observations to Vector Format:")
env = BlueFlatWrapper(env=cyborg)
obs, _ = env.reset()

print('Space:', env.observation_space('blue_agent_0'), '\n')
print('Observation:', obs['blue_agent_0'])