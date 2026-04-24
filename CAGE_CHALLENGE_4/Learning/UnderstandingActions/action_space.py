#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/A_Understanding_Actions/1_Action_Space/
# mac: venv/bin/python -m Learning.UnderstandingActions.action_space
# windows: .\venv\Scripts\python -m Learning.UnderstandingActions.action_space


from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.SimpleAgents.ConstantAgent import SleepAgent
from CybORG.Agents import SleepAgent

steps = 200
sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=SleepAgent, 
                                red_agent_class=SleepAgent,
                                steps=steps)
cyborg = CybORG(scenario_generator=sg, seed=1000)
cyborg.reset()

example_agent_name = 'blue_agent_0'
# example_agent_name = 'green_agent_0'
# example_agent_name = 'red_agent_0'
example_action_space = cyborg.get_action_space(example_agent_name)

pprint(example_action_space.keys())

pprint(example_action_space['action'])
# pprint(example_action_space['port'])


