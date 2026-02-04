#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/02_Looking_Around/1_Discover_Remote_Systems/#red-discover-remote-systems
# mac: venv/bin/python -m Learning.Red.DiscoverDeception.red_discover_deception
# windows: .\venv\Scripts\python -m Learning.Red.DiscoverDeception.red_discover_deception

from pprint import pprint
from ipaddress import IPv4Network, IPv4Address

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, FiniteStateRedAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import DiscoverRemoteSystems, AggressiveServiceDiscovery, Sleep, DiscoverDeception

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

action = DiscoverRemoteSystems(subnet=IPv4Network('10.0.96.0/24'), session=0, agent=red_agent_name)
results = cyborg.step(agent=red_agent_name, action=action)
obs = results.observation
pprint(obs)

print("*" * 50)
action = AggressiveServiceDiscovery(session=0, agent=red_agent_name, ip_address=IPv4Address('10.0.96.177'))
cyborg.step(agent=red_agent_name, action=action)

action = AggressiveServiceDiscovery(session=0, agent=red_agent_name, ip_address=IPv4Address('10.0.96.108'))
cyborg.step(agent=red_agent_name, action=action)


'''
print("*" * 50)
action = AggressiveServiceDiscovery(session=0, agent=red_agent_name, ip_address=IPv4Address('10.0.96.177'))
obs_1 = cyborg.step(agent=red_agent_name, action=action)
pprint(obs_1.observation)

print("*" * 50)
action = AggressiveServiceDiscovery(session=0, agent=red_agent_name, ip_address=IPv4Address('10.0.96.108'))
obs_2 = cyborg.step(agent=red_agent_name, action=action)
pprint(obs_2.observation)

'''

print("Host 1: ")
action = DiscoverDeception(session=0, agent=red_agent_name, ip_address=IPv4Address('10.0.96.177'))
cyborg.step(agent=red_agent_name, action=action)
results = cyborg.step(agent=red_agent_name, action=Sleep())
obs = results.observation
pprint(obs)

print("Host 2: ")
action = DiscoverDeception(session=0, agent=red_agent_name, ip_address=IPv4Address('10.0.96.108'))
cyborg.step(agent=red_agent_name, action=action)
results = cyborg.step(agent=red_agent_name, action=Sleep())
obs = results.observation
pprint(obs)