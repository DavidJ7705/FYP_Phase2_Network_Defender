#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/B_Blue_Actions/1_Monitor/
# mac: venv/bin/python -m Learning.Blue.blue_monitor
# windows: .\venv\Scripts\python -m Learning.Blue.blue_monitor


from CybORG.Tests.test_cc4.test_BlueEnterpriseWrapper import blue_agent_short
from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import Monitor

steps = 200
sg = EnterpriseScenarioGenerator(blue_agent_class = SleepAgent,
                                green_agent_class = SleepAgent,
                                red_agent_class = FiniteStateRedAgent,
                                steps = steps
                                )

cyborg = CybORG(scenario_generator=sg, seed = 1000)
blue_agent_name = 'blue_agent_0'

reset = cyborg.reset(agent = blue_agent_name)
initial_obs = reset.observation

# pprint(initial_obs.keys())

action = Monitor(0, blue_agent_name)
results = cyborg.step(agent=blue_agent_name, action = action)

step = 1
base_obs = results.observation

# print(f"step count: {step}")
# pprint(base_obs)

new_obs = base_obs

while new_obs == base_obs and step < steps:
    results = cyborg.step(agent = blue_agent_name, action = action)
    step = step+1
    new_obs = results.observation

print(f"step count: {step}")
pprint(new_obs)
