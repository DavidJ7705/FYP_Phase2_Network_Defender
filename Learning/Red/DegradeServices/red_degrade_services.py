#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/02_Looking_Around/1_Discover_Remote_Systems/#red-discover-remote-systems
# mac: venv/bin/python -m Learning.Red.DegradeServices.red_degrade_services
# windows: .\venv\Scripts\python -m Learning.Red.DegradeServices.red_degrade_services

from pprint import pprint
from ipaddress import IPv4Network, IPv4Address

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import DiscoverRemoteSystems, AggressiveServiceDiscovery, Sleep, PrivilegeEscalate, DegradeServices
from CybORG.Simulator.Actions.AbstractActions import ExploitRemoteService

sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=EnterpriseGreenAgent, 
                                red_agent_class=FiniteStateRedAgent,
                                steps=200)
cyborg = CybORG(scenario_generator=sg, seed=1000)
red_agent_name = 'red_agent_0'

print("*" *50)
print("Initial Observation")
reset = cyborg.reset(agent=red_agent_name)

print("*" *50)
print("Discover Remote Systems")
action = DiscoverRemoteSystems(subnet=IPv4Network('10.0.96.0/24'), session=0, agent=red_agent_name)
cyborg.step(agent=red_agent_name, action=action)

print("*" *50)
print("Service Discovery")
action = AggressiveServiceDiscovery(session=0, agent=red_agent_name, ip_address=IPv4Address('10.0.96.108'))
cyborg.step(agent=red_agent_name, action=action)

print("*" *50)
print("Exploit Service")
action = ExploitRemoteService(ip_address=IPv4Address('10.0.96.108'), session=0, agent=red_agent_name)
cyborg.step(agent=red_agent_name, action=action)
cyborg.step(agent=red_agent_name, action=Sleep())
cyborg.step(agent=red_agent_name, action=Sleep())
cyborg.step(agent=red_agent_name, action=Sleep())

print("*" *50)
print("Privilege Escalate Shell")
action = PrivilegeEscalate(hostname='contractor_network_subnet_user_host_4', session=0, agent=red_agent_name)
cyborg.step(agent=red_agent_name, action=action)
cyborg.step(agent=red_agent_name, action=Sleep())

print("*" *50)
print("Degrade Service")
action = DegradeServices(hostname='contractor_network_subnet_user_host_4', session=0, agent=red_agent_name)
results = cyborg.step(agent=red_agent_name, action=action)

results = cyborg.step(agent=red_agent_name, action=Sleep())
obs = results.observation
pprint(obs)