# Trained Agent Evaluation Results

## Overview

This directory contains the evaluation results for the **Graph-based PPO with Intra-agent Communication** blue team agent (by team Cybermonic) tested against three different red agent adversaries in the CybORG v4.0 CAGE Challenge 4 (CC4) environment.

Each evaluation was run for **50 episodes** with an episode length of **500 steps**. Five blue agents (`blue_agent_0` through `blue_agent_4`) cooperate to defend the network using an Inductive Graph PPO architecture.

## Results Summary

| Red Agent | Mean Reward | Std Dev | Best Episode | Worst Episode |
|---|---|---|---|---|
| SleepRedAgent (Baseline) | **-48.62** | 40.13 | -23 | -246 |
| FiniteStateRedAgent | **-185.74** | 50.12 | -106 | -298 |
| RandomSelectRedAgent | **-250.32** | 171.64 | -21 | -589 |

> **Note:** Rewards are negative; values closer to 0 indicate better defender performance.

## Red Agent Descriptions

### SleepRedAgent (Baseline)
The SleepRedAgent takes no actions throughout the episode. It serves as a **baseline** to measure how well the blue agents perform when there is no active adversary. The blue agents achieved a mean reward of **-48.62**, indicating that even without an attacker, some penalty is incurred from the cost of defensive actions.

### FiniteStateRedAgent
The FiniteStateRedAgent follows a deterministic, multi-stage attack strategy that progresses through a finite state machine (discovery, privilege escalation, lateral movement, impact). The blue agents achieved a mean reward of **-185.74** against this adversary. The relatively low standard deviation (50.12) shows consistent performance, suggesting the agent has learned a stable defensive policy against this structured attacker.

### RandomSelectRedAgent
The RandomSelectRedAgent selects actions uniformly at random from all available attack actions at each step. Despite being non-strategic, this agent proved to be the most challenging adversary, with the blue agents achieving a mean reward of **-250.32**. The high standard deviation (171.64) reflects the unpredictable nature of the random attacker — some episodes resulted in very low damage (-21) while others were catastrophic (-589). The bimodal distribution of rewards suggests that the defender either successfully contained the random attacks early or failed to respond to an unlucky sequence of effective attacks.

## Performance Analysis

### Comparison Graphs

The following graphs were generated from the evaluation data and are located in `tmp/comparison/`:

- **Performance Metrics** (`metrics.png`) — Bar chart comparing mean, median, max, and min rewards across all three red agents.
- **Cumulative Rewards** (`cumulative.png`) — Cumulative reward over episodes, showing the SleepRedAgent baseline accumulating far less penalty than the active adversaries.
- **Smoothed Learning Curves** (`smoothed_learning.png`) — Moving average (MA-20) of rewards per episode, showing the stability of the agent's performance over time.

### Key Observations

1. **Baseline Performance:** Against the SleepRedAgent, the defender incurs a small but consistent penalty (mean -48.62), representing the inherent cost of defensive monitoring actions even when no attack occurs.

2. **Structured vs Random Attacks:** The blue agent performs better against the structured FiniteStateRedAgent (-185.74) than the RandomSelectRedAgent (-250.32). This suggests the agent has learned to recognise and counter predictable attack patterns but struggles with the unpredictability of random actions.

3. **Consistency:** The FiniteStateRedAgent evaluation has the lowest standard deviation (50.12), indicating the most consistent defender performance. The RandomSelectRedAgent has the highest variance (171.64), reflecting the inherent unpredictability of the attacker.

4. **Worst-case Scenarios:** The worst single episode against RandomSelectRedAgent (-589) is significantly worse than against FiniteStateRedAgent (-298), highlighting the risk posed by unpredictable adversaries.

## How to Reproduce

```powershell
# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Set the PYTHONPATH (required on Windows)
$env:PYTHONPATH = "<path_to_project>\CAGE_CHALLENGE_4"

# Run evaluations against each red agent
python evaluation.py --max-eps 50 --red-agent SleepRedAgent --log
python evaluation.py --max-eps 50 --red-agent FiniteStateRedAgent --log
python evaluation.py --max-eps 50 --red-agent RandomSelectRedAgent --log
```

Results are saved to the `tmp/` directory, organised by red agent name and timestamp.
