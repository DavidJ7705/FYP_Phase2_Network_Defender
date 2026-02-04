#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/02_Looking_Around/1_Observations/#active-agents
# mac: venv/bin/python -m Learning.active_agents
# windows: .\venv\Scripts\python -m Learning.active_agents

from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent


print("-"*50)
print("Active Agents")
print("-"*50)

steps = 200
sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=EnterpriseGreenAgent, 
                                red_agent_class=FiniteStateRedAgent,
                                steps=steps)
cyborg = CybORG(scenario_generator=sg, seed=1234)

cyborg.reset()

agents = cyborg.active_agents

# Group by prefix (blue/green/red)
groups = {"blue": [], "green": [], "red": []}

for agent in agents:
    if agent.startswith("blue"):
        groups["blue"].append(agent)
    elif agent.startswith("green"):
        groups["green"].append(agent)
    elif agent.startswith("red"):
        groups["red"].append(agent)

# Pretty print
for colour, items in groups.items():
    title = colour.upper()
    print(f"{title} ({len(items)} agents):")
    for item in items:
        print(f"  • {item}")
    print()
