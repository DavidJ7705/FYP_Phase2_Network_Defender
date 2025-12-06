#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/A_Understanding_Actions/4_Invalid_Actions/
# mac: venv/bin/python -m Learning.Blue.DeployDecoy.deployDecoy
# windows: .\venv\Scripts\python -m Learning.Blue.DeployDecoy.deployDecoy

from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.SimpleAgents.ConstantAgent import SleepAgent
from CybORG.Simulator.Actions.AbstractActions.Analyse import Analyse
from Learning.Blue.DeployDecoy.root_shell_func import cyborg_with_root_shell_on_cns0

cyborg = cyborg_with_root_shell_on_cns0()

target_subnet = 'restricted_zone_a_subnet'
target_host = target_subnet + '_server_host_0'
target_ip = cyborg.environment_controller.state.hostname_ip_map[target_host]
shell_ip = cyborg.environment_controller.state.hostname_ip_map['contractor_network_subnet_server_host_3']

cyborg.environment_controller.state.hosts[target_host].processes = []
cyborg.environment_controller.state.hosts[target_host].services = {}