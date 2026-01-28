# mac: venv/bin/python -m Integration.Topology.extract_topology
# windows: .\venv\Scripts\python -m Integration.Topology.extract_topology


import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
import json

sg = EnterpriseScenarioGenerator(
    blue_agent_class=SleepAgent,
    green_agent_class=EnterpriseGreenAgent,
    red_agent_class=FiniteStateRedAgent,
    steps=200,
)
cyborg = CybORG(scenario_generator=sg, seed=42)

state = cyborg.environment_controller.state

print("="*60)
print("CYBORG TOPOLOGY (seed=42)")
print("="*60)

print(f"\nOVERVIEW:")
print(f"Total hosts: {len(state.hosts)}")
print(f"Total subnets: {len(state.subnets)}")

print(f"\nSUBNETS:")
for index, subnet_id in enumerate(state.subnets.keys(), start=1):
    print(f"\t{index} - {subnet_id}")

routers = [host for host in state.hosts.keys() if 'router' in host]
servers = [host for host in state.hosts.keys() if 'server' in host]
user_hosts = [host for host in state.hosts.keys() if 'user' in host]

print(f"\nHOST TYPES:")
print(f"  Routers: {len(routers)}")
print(f"  Servers: {len(servers)}")
print(f"  User hosts: {len(user_hosts)}")

print(f"\nSAMPLE HOSTS:")
print(f"  Routers: {routers[:3]}")
print(f"  Servers: {servers[:5]}")
print(f"  Users: {user_hosts[:5]}")

# Save summary
topology_data = {
    'total_hosts': len(state.hosts),
    'total_subnets': len(state.subnets),
    'subnets': [str(s) for s in state.subnets.keys()],
    'routers': routers,
    'servers': servers,
    'users': user_hosts
}

output_path = os.path.join(os.path.dirname(__file__), 'cyborg_topology_seed42.json')
with open(output_path, 'w') as f:
    json.dump(topology_data, f, indent=2)

print(f"\nSaved: {output_path}")
