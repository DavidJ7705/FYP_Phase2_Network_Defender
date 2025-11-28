#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/03_Actions/A_Understanding_Actions/4_Invalid_Actions/
# mac: venv/bin/python -m Learning.UnderstandingActions.valid_actions
# windows: .\venv\Scripts\python -m Learning.UnderstandingActions.valid_actions

from pprint import pprint

from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.SimpleAgents.ConstantAgent import SleepAgent
from CybORG.Simulator.Actions.AbstractActions.Analyse import Analyse

steps = 200
sg = EnterpriseScenarioGenerator(blue_agent_class = SleepAgent,
                                green_agent_class = SleepAgent,
                                red_agent_class = SleepAgent,
                                steps = steps
                                )

cyborg = CybORG(scenario_generator = sg, seed = 1000)
cyborg.reset()

example_agent_name = 'blue_agent_0'
example_action_space = cyborg.get_action_space(example_agent_name)

known_hostnames = [hn for hn, known in example_action_space['hostname'].items() if known]
target_hostname = known_hostnames[0]

example_action = Analyse(0, example_agent_name, target_hostname)

results = cyborg.step(agent = example_agent_name, action = example_action)

pprint(results.action)
pprint(results.observation)