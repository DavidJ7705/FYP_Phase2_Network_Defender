import os
import pickle
import numpy as np

from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent

class MindrakeAgent(BaseAgent):
    # agent that loads Team Mindrake's pre-trained model files
    def train(self, results):
        pass

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

    def __init__(self, model_file: str = None):
        if model_file is None:
            model_file = 'pretrained_agents/cage-challenge-2-public/logs/bandit_controller_15000.pkl'

        if os.path.exists(model_file):
            with open(model_file, 'rb') as f:
                self.model = pickle.load(f)
        else:
            self.model = None

    def get_action(self, observation, action_space):
        """gets an action from the agent that should be performed based on the agent's internal state and provided observation and action space"""
        if self.model is None:
            return np.random.randint(0, action_space)
        action, _states = self.model.predict(observation)
        return action
