#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/A_Understanding_Actions/2_Taking_an_Action/
# mac: venv/bin/python -m Learning.UnderstandingActions.take_action
# windows: .\venv\Scripts\python -m Learning.UnderstandingActions.take_action

#Using sleep agent since its good for understanding actions possible

from pprint import pprint

from CybORG import CybORG
from CybORG.Agents import SleepAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Simulator.Actions import Sleep

steps = 200     

# Initialising the scenario creator for CC4
sg = EnterpriseScenarioGenerator(
    blue_agent_class=SleepAgent,    # agent class used for the blue agents
    green_agent_class=SleepAgent,   # agent class used for the green agents
    red_agent_class=SleepAgent,     # agent class used for the red agents
    steps=steps                     # the number of steps to take for this episode
)

# Initialising the CybORG environment with the CC4 scenario generator and a fixed seed 
# (seed is optional and will be generated randomly if not supplied)
cyborg = CybORG(scenario_generator=sg, seed=1000)
cyborg.reset()


example_agent_name = 'blue_agent_0' # name of the agent that is going to take the action
# example_agent_name = 'green_agent_0' # name of the agent that is going to take the action
# example_agent_name = 'red_agent_0' # name of the agent that is going to take the action

example_action = Sleep() # action that the agent is going to take

# the environment takes a step with the given agent and action, and outputs the results from that step
results = cyborg.step(agent=example_agent_name, action=example_action)

# print the observations gained for that agent from that step
pprint(results.observation)