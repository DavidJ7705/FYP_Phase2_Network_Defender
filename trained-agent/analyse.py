
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from scipy import stats

def find_latest_run(base_path):
    base_path = Path(base_path)
    run_dirs = [d for d in base_path.glob("run_*") if d.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No run directories found in {base_path}")
    return max(run_dirs, key=lambda d: datetime.strptime(d.name.replace("run_", ""), "%Y-%m-%d_%H-%M-%S"))

def load_monitor_file(monitor_dir):
    monitor_dir = Path(monitor_dir)
    csv_file = list(monitor_dir.glob("*.csv"))
    if not csv_file:
        raise FileNotFoundError(f"No CSV files found in {monitor_dir}")
    return pd.read_csv(csv_file[0], skiprows=1)

def calculate_metrics(df):
    rewards_df = df['r']
    total_timesteps = df['l'].sum()
    return {
        'mean': rewards_df.mean(),
        'std': rewards_df.std(),
        'median': rewards_df.median(),
        'max': rewards_df.max(),
        "episodes": len(rewards_df),
        'success': np.mean(rewards_df > 0) * 100,
        'timesteps': total_timesteps
    }
root = Path(__file__).resolve().parents[2] if '__file__' in globals() else Path.cwd().parents[1]
docs = root / "documentation" / "frozenlake"

algorithms = {
    "Baseline": docs / "random-baseline",
    "A2C": docs / "a2c-frozenlake",
    "PPO": docs / "ppo-frozenlake",
    "DQN": docs / "dqn-frozenlake",    
}

dfs = {}
metrics = {}
runs = {}

for name, path in algorithms.items():
    run = find_latest_run(path)
    df = load_monitor_file(run / "monitor")
    dfs[name] = df
    runs[name] = run
    metrics[name] = calculate_metrics(df)

comparison_dir = docs / "comparison" / f"algorithms_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
graphs_dir = comparison_dir / "graphs"
graphs_dir.mkdir(parents=True, exist_ok=True)
def plot_metrics(metrics, out):
    labels = ["Mean", "Median", "Max", "Success Rate (%)"]
    algorithms = list(metrics.keys())

    data = {
        name: [
            metrics[name]['mean'],
            metrics[name].get('median', 0),
            metrics[name]['max'],
            metrics[name]['success'],
        ]
        for name in algorithms
    }

    x = np.arange(len(labels))
    w = 0.18 

    colors = {
        "Baseline": "#999999",
        "A2C": "#00b3f4",     
        "PPO": "#da1919",     
        "DQN": "#17aa07",     
    }

    plt.figure(figsize=(9, 5))
    for i, name in enumerate(algorithms):
        plt.bar(
            x + (i - len(algorithms)/2) * w + w/2,
            data[name],
            width=w,
            label=name,
            color=colors.get(name, f"C{i}"),
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
    colors = ["#999999", "#00b3f4", "#da1919", "#17aa07"]
    for (name, df), c in zip(dfs.items(), colors):
        plt.plot(np.cumsum(df["r"]), label=name, color=c, linewidth=1.8)
    plt.title("Cumulative Rewards — FrozenLake")
    plt.xlabel("Episode")
    plt.ylabel("Cumulative Reward")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out / "cumulative.png", dpi=300, bbox_inches="tight")
    plt.close()

def plot_overlay_with_mean(dfs, out, window=100):
    plt.figure(figsize=(10, 5))
    colors = {
        "Baseline": "#999999",
        "A2C": "#00b3f4",     
        "PPO": "#da1919",     
        "DQN": "#17aa07",     
    }

    for name, df in dfs.items():
        smooth = df["r"].rolling(window).mean()
        plt.plot(
            smooth,
            label=f"{name} (MA-{window})",
            color=colors[name],
            linewidth=2,
            alpha=0.8
        )

        plt.axhline(
            df["r"].mean(),
            color=colors[name],
            linestyle="--",
            alpha=0.5,
            linewidth=1
        )

    plt.title(f"Smoothed Learning Curves (MA-{window}) — FrozenLake", fontsize=13, pad=10)
    plt.xlabel("Episode", fontsize=11)
    plt.ylabel("Average Reward", fontsize=11)
    plt.legend(frameon=False, fontsize=9)
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(out / "smoothed_learning.png", dpi=300, bbox_inches="tight")
    plt.close()

    plot_metrics(metrics, graphs_dir)
    plot_cumulative(dfs, graphs_dir)
    plot_overlay_with_mean(dfs, graphs_dir, window=100)
    compare_pairs = [("Baseline", "A2C"), ("Baseline", "PPO"), ("Baseline", "DQN"),
            ("A2C", "PPO"), ("A2C", "DQN"), ("PPO", "DQN")]
    t_results = [(a, b, *stats.ttest_ind(dfs[a]["r"], dfs[b]["r"], equal_var=False)) for a, b in compare_pairs]

    summary = comparison_dir / "summary.md"
    with open(summary, "w", encoding="utf-8") as f:

        f.write(f"# FrozenLake Comparison - ({datetime.now():%Y-%m-%d %H:%M:%S})\n\n")
        f.write("| Algorithm | Mean | Max | Std | Success % | Episodes |\n")
        f.write("|------------|------|-----|-----|------------|-----------|\n")
        
        for n, m in metrics.items():
            f.write(f"| {n} | {m['mean']:.3f} | {m['max']:.1f} | {m['std']:.3f} | {m['success']:.2f} | {m['episodes']} |\n")

        f.write("\n## Welch’s t-test Results\n")
        for a, b, t, p in t_results:
            f.write(f"- {a} vs {b}: t = {t:.3f}, p = {p:.6f}\n")
            
        f.write("\n## Run Sources\n")
        for k, v in runs.items():
            f.write(f"- {k}: {v}\n")

    print(f"\nFrozenLake comparison saved to {comparison_dir}")
