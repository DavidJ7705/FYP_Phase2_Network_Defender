import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from datetime import datetime
import csv
import sys
import os

from CybORG import CybORG
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from submission import Submission

EPISODE_LENGTH = 100
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')

sg = EnterpriseScenarioGenerator(
    blue_agent_class=SleepAgent,
    green_agent_class=EnterpriseGreenAgent,
    red_agent_class=FiniteStateRedAgent,
    steps=EPISODE_LENGTH,
)
cyborg = CybORG(sg, "sim")
wrapped_cyborg = Submission.wrap(cyborg)
observations, _ = wrapped_cyborg.reset()