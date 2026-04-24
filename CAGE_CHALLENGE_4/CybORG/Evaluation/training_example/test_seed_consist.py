from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent

print("="*60)
print("Test 1: Creating CybORG a bunch of times with same seed (42)")
print("="*60)

for run in range(3):
    sg = EnterpriseScenarioGenerator(
        blue_agent_class=SleepAgent,
        green_agent_class=EnterpriseGreenAgent,
        red_agent_class=FiniteStateRedAgent,
        steps=200,
    )
    cyborg = CybORG(scenario_generator=sg, seed=42)
    
    state = cyborg.environment_controller.state
    num_hosts = len(state.hosts)
    host_names = sorted(state.hosts.keys())
    
    print(f"\nRun {run + 1}:")
    print(f"  Number of hosts: {num_hosts}")
    print(f"  First 5 hosts: {host_names[:5]}")
    print(f"  Subnets: {list(state.subnets.keys())}")

print("\n")
print("="*60)
print("Test 2: Creating CybORG a bunch of times with same seed (67)")
print("="*60)

for run in range(3):
    sg = EnterpriseScenarioGenerator(
        blue_agent_class=SleepAgent,
        green_agent_class=EnterpriseGreenAgent,
        red_agent_class=FiniteStateRedAgent,
        steps=200,
    )
    cyborg = CybORG(scenario_generator=sg, seed=67)
    
    state = cyborg.environment_controller.state
    num_hosts = len(state.hosts)
    host_names = sorted(state.hosts.keys())
    
    print(f"\nRun {run + 1}:")
    print(f"  Number of hosts: {num_hosts}")
    print(f"  First 5 hosts: {host_names[:5]}")
    print(f"  Subnets: {list(state.subnets.keys())}")

print("\n")
print("="*60)
print("Test 3: Changed seeds")
print("="*60)

for seed in [42, 100, 999]:
    sg = EnterpriseScenarioGenerator(
        blue_agent_class=SleepAgent,
        green_agent_class=EnterpriseGreenAgent,
        red_agent_class=FiniteStateRedAgent,
        steps=200,
    )
    cyborg = CybORG(scenario_generator=sg, seed=seed)
    
    state = cyborg.environment_controller.state
    num_hosts = len(state.hosts)
    
    print(f"\nSeed {seed}:")
    print(f"  Number of hosts: {num_hosts}")