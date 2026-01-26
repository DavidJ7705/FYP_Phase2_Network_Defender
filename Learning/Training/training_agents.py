#https://cage-challenge.github.io/cage-challenge-4/pages/tutorials/01_Getting_Started/3_Training_Agents/
# mac: venv/bin/python -m Learning.Training.training_agents
# windows: .\venv\Scripts\python -m Learning.Training.training_agents


from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents.Wrappers import EnterpriseMAE

from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent

from ray.tune import register_env
from ray.rllib.algorithms.ppo import PPOConfig, PPO
from ray.rllib.algorithms.dqn import DQNConfig, DQN
from ray.rllib.policy.policy import PolicySpec

def env_creator_CC4(env_config: dict):
    sg = EnterpriseScenarioGenerator(
        blue_agent_class=SleepAgent,
        green_agent_class=EnterpriseGreenAgent,
        red_agent_class=FiniteStateRedAgent,
        steps=1000
    )
    cyborg = CybORG(scenario_generator=sg)
    env = EnterpriseMAE(env=cyborg)
    return env

register_env(name="CC4", env_creator=lambda config: env_creator_CC4(config))
env = env_creator_CC4({})


NUM_AGENTS = 5
POLICY_MAP = {f"blue_agent_{i}": f"Agent{i}" for i in range(NUM_AGENTS)}

def policy_mapper(agent_id, episode, worker, **kwargs):
    return POLICY_MAP[agent_id]


algo_config = (
    PPOConfig()
    .environment(env="CC4")
    .debugging(logger_config={"logdir":"logs/PPO_Example", "type":"ray.tune.logger.TBXLogger"})
    .multi_agent(policies={
        ray_agent: PolicySpec(
            policy_class=None,
            observation_space=env.observation_space(cyborg_agent),
            action_space=env.action_space(cyborg_agent),
            config={"gamma": 0.85},
        ) for cyborg_agent, ray_agent in POLICY_MAP.items()
    },
    policy_mapping_fn=policy_mapper
))



algo = algo_config.build()

for i in range(5):
    train_info=algo.train()

algo.save("results")