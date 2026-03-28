import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import audioop  # type: ignore
except ImportError:
    import pyaudioop as _pyaudioop

    sys.modules["audioop"] = _pyaudioop

import gradio as gr
import matplotlib.pyplot as plt # type: ignore
import numpy as np

# Add src to path
sys.path.insert(0, "./src")

from demo import run_showdown_for_difficulty, run_episode_with_grids, GreedyPolicy, RandomPolicy, PassPolicy, EpsilonGreedyPolicy

def run_policy_showdown(difficulty):
    result = run_showdown_for_difficulty(difficulty)
    # Parse result to get scores for plotting
    lines = result.split('\n')
    policies = []
    scores = []
    for line in lines:
        if '|' in line and 'Score:' in line:
            parts = line.split('|')
            policy = parts[0].strip()
            score_str = parts[1].split(':')[1].split('/')[0].strip()
            score = float(score_str)
            policies.append(policy)
            scores.append(score)
    fig = plot_scores(policies, scores, difficulty)
    return result, fig

def plot_scores(policies, scores, difficulty):
    fig, ax = plt.subplots()
    ax.bar(policies, scores, color='skyblue')
    ax.set_ylabel('Average Score /100')
    ax.set_title(f'Policy Performance Comparison ({difficulty.capitalize()})')
    plt.xticks(rotation=45, ha='right')
    return fig

def format_episode_summary(policy_name, difficulty, report):
    return "\n".join([
        f"Policy: {policy_name} | Difficulty: {difficulty}",
        f"Score: {report['score']:.1f}/100 | Total Reward: {report['total_reward']:+.1f}",
        f"Waves: {report['waves_completed']}/{report['total_waves']} | Kills: {report['kills']} | Leaks: {report['leaks']}",
        f"Towers: {report['towers_placed']} | Base HP: {report['base_hp_remaining']} | Won: {report['game_won']}",
    ])

def run_single_episode(policy_name, difficulty):
    policies = {
        "Random": RandomPolicy(),
        "Always Pass": PassPolicy(),
        "Greedy Placer": GreedyPolicy(),
        "Epsilon-Greedy": EpsilonGreedyPolicy(),
    }
    policy = policies[policy_name]
    report, grids = run_episode_with_grids(policy, difficulty)
    grid_text = "\n\n".join(grids[-6:])  # Show the most recent grids without overwhelming the UI
    summary = format_episode_summary(policy_name, difficulty, report)
    return summary, grid_text

# Gradio interface
with gr.Blocks(title="Tower Defense RL Policy Showdown") as demo:
    gr.Markdown("# 🏰 Tower Defense RL — Policy Showdown Demo")
    gr.Markdown("Compare different AI policies in the Tower Defense game across difficulty levels.")

    with gr.Tabs():
        with gr.TabItem("Policy Showdown"):
            difficulty1 = gr.Dropdown(choices=["easy", "medium", "hard"], value="easy", label="Select Difficulty")
            run_btn1 = gr.Button("Run Showdown")
            output1 = gr.Textbox(label="Results", lines=12, interactive=False)
            plot_output = gr.Plot(label="Performance Chart")
            run_btn1.click(fn=run_policy_showdown, inputs=difficulty1, outputs=[output1, plot_output])

        with gr.TabItem("Single Episode Visualization"):
            policy = gr.Dropdown(choices=["Random", "Always Pass", "Greedy Placer", "Epsilon-Greedy"], value="Greedy Placer", label="Select Policy")
            difficulty2 = gr.Dropdown(choices=["easy", "medium", "hard"], value="easy", label="Select Difficulty")
            run_btn2 = gr.Button("Run Episode")
            summary = gr.Textbox(label="Episode Summary", lines=4, interactive=False)
            grid_display = gr.Textbox(label="Grid Visualization", lines=20, interactive=False)
            run_btn2.click(fn=run_single_episode, inputs=[policy, difficulty2], outputs=[summary, grid_display])

if __name__ == "__main__":
    demo.launch()
