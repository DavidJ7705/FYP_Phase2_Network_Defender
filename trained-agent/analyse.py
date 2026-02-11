import os
import json
import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from scipy import stats

TMP_DIR = Path(__file__).resolve().parent / "tmp"
OUTPUT_DIR = Path(__file__).resolve().parent
RED_AGENTS = ["FiniteStateRedAgent", "RandomSelectRedAgent", "SleepRedAgent"]
 
COLORS = {
    "FiniteStateRedAgent": "#da1919",
    "RandomSelectRedAgent": "#f39c12",
    "SleepRedAgent": "#17aa07",
}
 
LABELS = {
    "FiniteStateRedAgent": "FiniteState (Primary)",
    "RandomSelectRedAgent": "RandomSelect",
    "SleepRedAgent": "Sleep (Baseline)",
}

def find_latest_run(agent_name):
    agent_dir = TMP_DIR / agent_name
    if not agent_dir.exists():
        return None
    runs = [d for d in agent_dir.iterdir() if d.is_dir()]
    if not runs:
        return None
    return max(runs, key=lambda d: d.name)

def load_results():
    summaries = {}
    episode_dfs = {}

    for agent in RED_AGENTS:
        run_path = find_latest_run(agent)
        if run_path is None:
            print(f"No runs found for {agent}")
            continue
    
        json_path = run_path / "summary.json"
        if json_path.exists():
            with open(json_path, "r") as f:
                data = json.load(f)
            summaries[agent] = {
                "mean": data["reward"]["mean"],
                "stdev": data["reward"]["stdev"],
                "episodes": data["parameters"]["max_episodes"],
                "episode_length": data["parameters"]["episode_length"],
                "elapsed_time": data["time"]["elapsed"],
                "run_folder": run_path.name,
            }
            print(f"Loaded {agent}: mean={data['reward']['mean']:.2f}, stdev={data['reward']['stdev']:.2f}")

        rewards_path = run_path / "episode_rewards.csv"
        if rewards_path.exists():
            episode_dfs[agent] = pd.read_csv(rewards_path)
        else:
            print(f"  No episode_rewards.csv for {agent} — per-episode graphs will be skipped for this agent.")
 
    return summaries, episode_dfs


def calculate_metrics(df):
    rewards_df = df['reward']
    return {
        'mean': rewards_df.mean(),
        'std': rewards_df.std(),
        'median': rewards_df.median(),
        "min": rewards_df.min(),
        'max': rewards_df.max(),
        "episodes": len(rewards_df),
    }



def plot_metrics(metrics, out):
    labels = ["Mean", "Median", "Max", "Min"]
    agents = list(metrics.keys())

    data = {
        name: [
            metrics[name]['mean'],
            metrics[name].get('median', 0),
            metrics[name]['max'],
            metrics[name]['min'],
        ]
        for name in agents
    }

    x = np.arange(len(labels))
    w = 0.18 

    plt.figure(figsize=(9, 5))
    for i, name in enumerate(agents):
        plt.bar(
            x + (i - len(agents)/2) * w + w/2,
            data[name],
            width=w,
            label=LABELS.get(name,name),
            color=COLORS.get(name, f"C{i}"),
            alpha=0.9
        )

    plt.xticks(x, labels, fontsize=10)
    plt.ylabel("Value", fontsize=11)
    plt.title("FrozenLake — Algorithm Performance Metrics", fontsize=13, weight="bold")
    plt.legend(frameon=False, fontsize=9, ncol=2)
    plt.grid(axis='y', alpha=0.25)
    plt.tight_layout()
    plt.savefig(out / "metrics.png", dpi=300, bbox_inches='tight')
    plt.close()

def plot_cumulative(dfs, out):
    plt.figure(figsize=(10, 5))

    for name, df in dfs.items():
        plt.plot(
            np.cumsum(df["reward"]), 
            label=LABELS.get(name,name),
            color=COLORS.get(name),
            linewidth=1.8
    )


    plt.title("Cumulative Rewards Over Episodes— CC4")
    plt.xlabel("Episode")
    plt.ylabel("Cumulative Reward")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out / "cumulative.png", dpi=300, bbox_inches="tight")
    plt.close()

def plot_overlay_with_mean(dfs, out, window=100):
    plt.figure(figsize=(10, 5))


    for name, df in dfs.items():
        smooth = df["reward"].rolling(window, min_periods = 1).mean()
        plt.plot(
            smooth,
            label=f"{LABELS.get(name,name)} (MA-{window})",
            color=COLORS.get(name),
            linewidth=2,
            alpha=0.8
        )
        plt.axhline(
            df["reward"].mean(),
            color=COLORS.get(name),
            linestyle="--",
            alpha=0.5,
            linewidth=1
        )

    plt.title(f"Smoothed Learning Curves (MA-{window}) — CC4", fontsize=13, pad=10)
    plt.xlabel("Episode", fontsize=11)
    plt.ylabel("Average Reward", fontsize=11)
    plt.legend(frameon=False, fontsize=9)
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(out / "smoothed_learning.png", dpi=300, bbox_inches="tight")
    plt.close()




if __name__ == "__main__":

    print("Loading results from tmp/...\n")
    summaries, episode_dfs = load_results()
 
    if not summaries:
        print("No results found. Run evaluations first.")
        exit(1)
 
    # Create comparison output dir: tmp/comparison/run_TIMESTAMP/
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    comparison_dir = TMP_DIR / "comparison" / f"run_{run_id}"
    graphs_dir = comparison_dir / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)

    # Graphs
    print(f"\nGenerating graphs in {graphs_dir}/")
 
    if episode_dfs:
        metrics = {name: calculate_metrics(df) for name, df in episode_dfs.items()}
        plot_metrics(metrics, graphs_dir)
        plot_cumulative(episode_dfs, graphs_dir)
        plot_overlay_with_mean(episode_dfs, graphs_dir, window=20)

    else:
        print("No per-episode data found. Add episode_rewards.csv saving to evaluation.py.")
 
    print("\nDone!")