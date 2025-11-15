#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/01_Getting_Started/2_Getting_Started/
from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.Wrappers import BlueEnterpriseWrapper, BlueFlatWrapper
import numpy as np
from rich import print


sg = EnterpriseScenarioGenerator()
cyborg = CybORG(scenario_generator=sg)

# print(cyborg.active_agents)

env = BlueEnterpriseWrapper(env=cyborg)
obs, _ = env.reset()


# print(obs.keys())
# print(env.subnets('blue_agent_0'))
# print(obs['blue_agent_0'])


# print(env.action_space('blue_agent_0'))
# print(len(env.action_labels('blue_agent_0')))
# print(env.action_labels('blue_agent_0'))

# actions = {'blue_agent_0' : 42}
# obs, reward, terminated, truncated, info = env.step(actions)
# print(reward['blue_agent_0'])

# actions = {'blue_agent_0' : 42}
# messages = {'blue_agent_0' : np.array([1,0,0,0,0,0,0,0])}
# obs, reward, terminated, truncated, info = env.step(actions, messages=messages)
# print(obs['blue_agent_1']['message'])

env = BlueFlatWrapper(env=cyborg)
obs, _ = env.reset()

print('Space:', env.observation_space('blue_agent_0'), '\n')
print('Observation:', obs['blue_agent_0'])