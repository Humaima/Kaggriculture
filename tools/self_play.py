"""
Phase 6 self-play test harness. Runs main.py against:
  - built-in "random" (N episodes, since random adds real variance)
  - built-in "starter" (deterministic vs deterministic -> 1 episode suffices)
  - agents/wheat_loop_v1.py, our own frozen Phase 3 snapshot (also deterministic)

Logs every episode's result to results/self_play_log.csv (append mode, so
you can track results across runs over time) and prints summary stats.

Run from the project root:
    .venv/bin/python tools/self_play.py
"""

import csv
import datetime
import os
import sys

from kaggle_environments import make

FULL_SEASON_STEPS = 720
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(PROJECT_ROOT, "results", "self_play_log.csv")

# (label, opponent, episode_count, is_stochastic)
# "random" is doubly stochastic (its own move choice, plus environment
# weed/shop randomness) so we sample it multiple times with different
# seeds. The other two use fixed seeds so results are exactly reproducible
# run to run -- any difference you see after a planner change is real,
# not environment noise (weedSpawnChance and random shop unlocks mean
# even a deterministic-vs-deterministic matchup varies without a fixed seed).
MATCHUPS = [
    ("random", "random", 5, True, None),
    ("starter", "starter", 1, False, 42),
    ("self_v1_wheat_loop", os.path.join(PROJECT_ROOT, "agents", "wheat_loop_v1.py"), 1, False, 42),
]


def run_episode(opponent, seed=None):
    config = {"episodeSteps": FULL_SEASON_STEPS}
    if seed is not None:
        config["seed"] = seed
    env = make("kaggriculture", configuration=config, debug=True)
    env.run(["main.py", opponent])
    final = env.steps[-1]
    my_reward, my_status = final[0]["reward"], final[0]["status"]
    opp_reward, opp_status = final[1]["reward"], final[1]["status"]
    return my_reward, my_status, opp_reward, opp_status


def ensure_log_header():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    is_new = not os.path.exists(LOG_PATH)
    if is_new:
        with open(LOG_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "matchup_label", "episode_index",
                "my_reward", "my_status", "opp_reward", "opp_status", "outcome",
            ])


def append_log_row(matchup_label, episode_index, my_reward, my_status, opp_reward, opp_status, outcome):
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.datetime.now().isoformat(timespec="seconds"),
            matchup_label, episode_index,
            my_reward, my_status, opp_reward, opp_status, outcome,
        ])


def main():
    ensure_log_header()
    print(f"Logging results to {LOG_PATH}\n")

    for label, opponent, n_episodes, is_stochastic, fixed_seed in MATCHUPS:
        rewards = []
        error_seen = False
        for i in range(n_episodes):
            episode_seed = fixed_seed if fixed_seed is not None else None
            my_reward, my_status, opp_reward, opp_status = run_episode(opponent, seed=episode_seed)
            outcome = "WIN" if my_reward > opp_reward else (
                "LOSS" if my_reward < opp_reward else "TIE"
            )
            if "ERROR" in (my_status, opp_status):
                error_seen = True
            append_log_row(label, i, my_reward, my_status, opp_reward, opp_status, outcome)
            rewards.append((my_reward, opp_reward, outcome))

        my_rewards = [r[0] for r in rewards]
        opp_rewards = [r[1] for r in rewards]
        wins = sum(1 for r in rewards if r[2] == "WIN")
        mean_my = sum(my_rewards) / len(my_rewards)
        mean_opp = sum(opp_rewards) / len(opp_rewards)

        flag = "  <-- ERROR DETECTED" if error_seen else ""
        print(f"vs {label:22s} n={n_episodes}  win_rate={wins}/{n_episodes}  "
              f"mean_me={mean_my:9.1f}  mean_opp={mean_opp:9.1f}  "
              f"margin={mean_my - mean_opp:+9.1f}{flag}")
        if is_stochastic and n_episodes > 1:
            spread = max(my_rewards) - min(my_rewards)
            print(f"    (my_reward range across episodes: {min(my_rewards):.0f}"
                  f" - {max(my_rewards):.0f}, spread={spread:.0f})")

    print(f"\nFull episode-by-episode log: {LOG_PATH}")


if __name__ == "__main__":
    main()
