#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/B_Blue_Actions/2_Analyse/
# mac: venv/bin/python -m Learning.Blue.Analyse.analyse
# windows: .\venv\Scripts\python -m Learning.Blue.Analyse.analyse


from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import Analyse

steps = 200
sg = EnterpriseScenarioGenerator(blue_agent_class = SleepAgent,
                                green_agent_class = EnterpriseGreenAgent,
                                red_agent_class = FiniteStateRedAgent,
                                steps = steps
                                )

cyborg = CybORG(scenario_generator=sg, seed = 1000)
cyborg.reset()

blue_agent_name = 'blue_agent_0'
blue_action_space = cyborg.get_action_space(blue_agent_name)

action = Analyse(session=0, agent=blue_agent_name, hostname='restricted_zone_a_subnet_server_host_0')

results = cyborg.step(agent = blue_agent_name, action = action)
print("step 1:",results.observation)
results = cyborg.step(agent = blue_agent_name)
print("step 2:",results.observation)

