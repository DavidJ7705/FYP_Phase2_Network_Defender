#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/B_Blue_Actions/1_Monitor/
# mac: venv/bin/python -m Learning.Blue.Monitor.blue_monitor_green
# windows: .\venv\Scripts\python -m Learning.Blue.Monitor.blue_monitor_green


from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import Monitor

print("-"*50)
print("CybORG CAGE Challenge 4 - Blue Monitor Action on Green Agent")
print("-"*50)

steps = 200
sg = EnterpriseScenarioGenerator(blue_agent_class = SleepAgent,
                                green_agent_class = EnterpriseGreenAgent,
                                red_agent_class = SleepAgent,
                                steps = steps
                                )

cyborg = CybORG(scenario_generator=sg, seed = 1000)
cyborg.reset()

blue_agent_name = 'blue_agent_0'
blue_action_space = cyborg.get_action_space(blue_agent_name)

action = Monitor(0, blue_agent_name)
results = cyborg.step(agent=blue_agent_name, action = action)

step = 1
base_obs = results.observation

new_obs = base_obs

while new_obs == base_obs and step < steps:
    results = cyborg.step(agent = blue_agent_name, action = action)
    step = step+1
    new_obs = results.observation

print(f"step count: {step}")
pprint(new_obs)
