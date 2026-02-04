#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/C_Red_Actions/2_Service_Discovery/
# mac: venv/bin/python -m Learning.Red.ServiceDiscovery.red_service_discovery
# windows: .\venv\Scripts\python -m Learning.Red.ServiceDiscovery.red_service_discovery

from pprint import pprint
from ipaddress import IPv4Network, IPv4Address

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import AggressiveServiceDiscovery, StealthServiceDiscovery, Sleep

sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=EnterpriseGreenAgent, 
                                red_agent_class=FiniteStateRedAgent,
                                steps=200)
cyborg = CybORG(scenario_generator=sg, seed=1000)
red_agent_name = 'red_agent_0'

reset = cyborg.reset(agent=red_agent_name)
initial_obs = reset.observation
pprint(initial_obs)
