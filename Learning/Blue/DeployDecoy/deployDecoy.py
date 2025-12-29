#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/A_Understanding_Actions/4_Invalid_Actions/
# mac: venv/bin/python -m Learning.Blue.DeployDecoy.deployDecoy
# windows: .\venv\Scripts\python -m Learning.Blue.DeployDecoy.deployDecoy

from Learning.Blue.Analyse.analyse import blue_agent_name
from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.SimpleAgents.ConstantAgent import SleepAgent
from CybORG.Simulator.Actions.AbstractActions.Analyse import Analyse
from CybORG.Simulator.Actions.ConcreteActions.DecoyActions.DeployDecoy import DeployDecoy
from CybORG.Simulator.Actions.AbstractActions.DiscoverNetworkServices import StealthServiceDiscovery
from CybORG.Simulator.Actions.AbstractActions.ExploitRemoteService import ExploitRemoteService
from Learning.Blue.DeployDecoy.root_shell_func import cyborg_with_root_shell_on_cns0

cyborg = cyborg_with_root_shell_on_cns0()

target_subnet = 'restricted_zone_a_subnet'
target_host = target_subnet + '_server_host_0'
target_ip = cyborg.environment_controller.state.hostname_ip_map[target_host]
shell_ip = cyborg.environment_controller.state.hostname_ip_map['contractor_network_subnet_server_host_3']

cyborg.environment_controller.state.hosts[target_host].processes = []
cyborg.environment_controller.state.hosts[target_host].services = {}

action = DeployDecoy(session = 0, agent = blue_agent_name, hostname = target_host)
action.duration = 1
obs, _, _, _, = cyborg.parallel_step(actions = {blue_agent_name: action})

print("deployed decoy")
print("Blue:")
print(obs[blue_agent_name])
print("\n")

red_agent_name = 'red_agent_0'

red_action = StealthServiceDiscovery(session=0, agent=red_agent_name, ip_address=target_ip)
red_action.duration = 1
red_action.detection_rate = 0
obs, _, _, _ = cyborg.parallel_step(actions={red_agent_name: red_action})

print("StealthServiceDiscovery:")
print("Red:")
pprint(obs[red_agent_name])
print("\n")
print("Blue:")
pprint(obs[blue_agent_name])
print("\n")

action_2 = ExploitRemoteService(ip_address=target_ip, session=0, agent=red_agent_name)
action_2.duration = 1
obs_2, _, _, _ = cyborg.parallel_step(actions={red_agent_name: action_2})

print("ExploitRemoteService:")
print("Red:")
pprint(obs_2[red_agent_name])
print("\n")
print("Blue:")
pprint(obs_2[blue_agent_name])
print("\n")
