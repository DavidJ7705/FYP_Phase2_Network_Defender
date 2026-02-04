#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/C_Red_Actions/8_Withdraw/
# mac: venv/bin/python -m Learning.Red.Withdraw.red_withdraw
# windows: .\venv\Scripts\python -m Learning.Red.Withdraw.red_withdraw

from pprint import pprint
from ipaddress import IPv4Network, IPv4Address

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import DiscoverRemoteSystems, AggressiveServiceDiscovery, Sleep, PrivilegeEscalate, Withdraw, DegradeServices
from CybORG.Simulator.Actions.AbstractActions import ExploitRemoteService
from CybORG.Simulator.Actions.ConcreteActions import Withdraw

sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=EnterpriseGreenAgent, 
                                red_agent_class=FiniteStateRedAgent,
                                steps=200)
cyborg = CybORG(scenario_generator=sg, seed=1000)
red_agent_name = 'red_agent_0'

reset = cyborg.reset(agent=red_agent_name)
initial_obs = reset.observation
pprint(initial_obs)

action = DiscoverRemoteSystems(subnet=IPv4Network('10.0.96.0/24'), session=0, agent=red_agent_name)
results = cyborg.step(agent=red_agent_name, action=action)
obs = results.observation
pprint(obs)

action = AggressiveServiceDiscovery(session=0, agent=red_agent_name, ip_address=IPv4Address('10.0.96.108'))
cyborg.step(agent=red_agent_name, action=action)

action = ExploitRemoteService(ip_address=IPv4Address('10.0.96.108'), session=0, agent=red_agent_name)
cyborg.step(agent=red_agent_name, action=action)
cyborg.step(agent=red_agent_name, action=Sleep())
results = cyborg.step(agent=red_agent_name, action=Sleep())
obs = results.observation
pprint(obs)

action = PrivilegeEscalate(hostname='contractor_network_subnet_user_host_5', session=0, agent=red_agent_name)
results = cyborg.step(agent=red_agent_name, action=action)
obs = results.observation
pprint(obs)


action = Withdraw(session=0, agent=red_agent_name, 
                  ip_address=IPv4Address('10.0.96.73'),
                  hostname='contractor_network_subnet_user_host_4')
results = cyborg.step(agent=red_agent_name, action=action)
obs = results.observation
pprint(obs)

action = DegradeServices(hostname='contractor_network_subnet_user_host_5', session=0, agent=red_agent_name)
results = cyborg.step(agent=red_agent_name, action=action)
obs = results.observation
pprint(obs)