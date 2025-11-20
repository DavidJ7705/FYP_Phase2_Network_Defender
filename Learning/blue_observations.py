#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/02_Looking_Around/1_Observations/#blue-observations
# to run: venv/bin/python -m Learning.blue_observations
from pprint import pprint
from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent
from CybORG.Simulator.Actions import Sleep

steps = 1000
sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent, 
                                green_agent_class=EnterpriseGreenAgent, 
                                red_agent_class=SleepAgent,
                                steps=steps)
cyborg = CybORG(scenario_generator=sg, seed=1234)

reset = cyborg.reset(agent='blue_agent_0')
initial_obs = reset.observation

print("\nBlue Agent 0: Initial Observation")
print("\nKeys Only: \n")
pprint(initial_obs.keys())

print("\nSingle Host: \n")
pprint(initial_obs[list(initial_obs.keys())[1]])

#Uneventful Steps
obs_1 = cyborg.step(agent='blue_agent_0', action=Sleep()).observation
print("\nBlue Agent 0: Step #1 \n")
pprint(obs_1)

#eventfull steps
for agent_name, ai in cyborg.environment_controller.agent_interfaces.items():
    if 'green' in agent_name and isinstance(ai.agent, EnterpriseGreenAgent):
        ai.agent.fp_detection_rate = 1.0

obs_2 = cyborg.step(agent='blue_agent_0', action=Sleep()).observation

print("\nBlue Agent 0: Step #2 with Green False Positive \n")
pprint(obs_2)