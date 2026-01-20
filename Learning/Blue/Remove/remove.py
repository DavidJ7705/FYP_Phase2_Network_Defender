#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/B_Blue_Actions/4_Remove/
# mac: venv/bin/python -m Learning.Blue.Remove.remove
# windows: .\venv\Scripts\python -m Learning.Blue.Remove.remove

from Learning.Blue.Remove.red_shell_func_2 import get_shell_on_rzas0, target_host
from Learning.Blue.Remove.root_shell_func import cyborg_with_root_shell_on_cns0
from pprint import pprint
from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent
from CybORG.Simulator.Actions import Remove

blue_agent_name = 'blue_agent_0'
red_agent_name = ['red_agent_0', 'red_agent_1']

# start with a cyborg environment with a user shell on `restricted_zone_a_subnet_server_host_0`
cyborg = get_shell_on_rzas0(cyborg=cyborg_with_root_shell_on_cns0(), shell_type='user')
print("*"*50)
env = cyborg.environment_controller
target_ip = env.state.hostname_ip_map[target_host]

print("Red: Before Remove")
pprint(cyborg.get_observation(agent=red_agent_name[1]))
print("\n")

# Run the Remove action
blue_action = Remove(session=0, agent=blue_agent_name, hostname=target_host)
blue_action.duration = 1
obs, _, _, _ = cyborg.parallel_step(actions={blue_agent_name: blue_action})
assert obs['blue_agent_0']['success'] == True

print("Blue: Remove Step")
pprint(obs['blue_agent_0'])
print("\n")

print("Red: Remove Step")
pprint(obs[red_agent_name[1]] if red_agent_name[1] in cyborg.active_agents else "not an active agents")