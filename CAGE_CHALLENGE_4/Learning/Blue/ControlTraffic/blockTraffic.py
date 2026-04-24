#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/B_Blue_Actions/6_Control_Traffic/
# mac: venv/bin/python -m Learning.Blue.ControlTraffic.blockTraffic
# windows: .\venv\Scripts\python -m Learning.Blue.ControlTraffic.blockTraffic

from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions.ConcreteActions.ControlTraffic import BlockTrafficZone

steps = 200
sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=EnterpriseGreenAgent, 
                                red_agent_class=FiniteStateRedAgent,
                                steps=steps)
cyborg = CybORG(scenario_generator=sg, seed=1000)
cyborg.reset()

blue_agent_name = 'blue_agent_0'
action_space = cyborg.get_action_space(blue_agent_name)

action = BlockTrafficZone(session=0, agent=blue_agent_name, from_subnet='restricted_zone_a_subnet', to_subnet='restricted_zone_b_subnet')

results = cyborg.step(agent=blue_agent_name, action=action)
obs = results.observation
pprint(obs)