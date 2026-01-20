#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/02_Looking_Around/1_Discover_Remote_Systems/#red-discover-remote-systems
# mac: venv/bin/python -m Learning.Red.PrivilegeEscalate.red_privilege_escalate
# windows: .\venv\Scripts\python -m Learning.Red.PrivilegeEscalate.red_privilege_escalate

from pprint import pprint
from ipaddress import IPv4Network, IPv4Address

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import PrivilegeEscalate

sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=EnterpriseGreenAgent, 
                                red_agent_class=FiniteStateRedAgent,
                                steps=200)
cyborg = CybORG(scenario_generator=sg, seed=1000)
red_agent_name = 'red_agent_0'

reset = cyborg.reset(agent=red_agent_name)
initial_obs = reset.observation
pprint(initial_obs)

print("*" * 50)