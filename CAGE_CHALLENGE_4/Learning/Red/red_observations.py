#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/02_Looking_Around/1_Observations/#red-observations
# mac: venv/bin/python -m Learning.Red.red_observations
# windows: .\venv\Scripts\python -m Learning.Red.red_observations


from pprint import pprint
from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent
from CybORG.Simulator.Actions.AbstractActions import PrivilegeEscalate

print("-"*50)
print("Red Agent Observations")
print("-"*50)

steps = 200
sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=SleepAgent, 
                                red_agent_class=SleepAgent,
                                steps=steps)
cyborg = CybORG(scenario_generator=sg, seed=1234)

reset = cyborg.reset(agent='red_agent_0')
first_session_host = list(reset.observation.keys())[1]
initial_obs = reset.observation

print("\nRed Agent 0: Initial Observation \n")
pprint(initial_obs)