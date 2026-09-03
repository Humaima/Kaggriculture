"""
Quick manual probe: run the planner against 'random' for a handful of
steps and print what it decided each turn, so you can eyeball the
farmer's movement/action choices without a full season.

Run from the project root:
    .venv/bin/python tools/probe_planner.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kaggle_environments import make

from strategy.planner import decide


def probe(obs):
    action = decide(obs)
    me = obs["farms"][obs["player"]]
    fx, fy = me["farmer"]
    print(f"step={obs['step']:2d} pos=({fx},{fy}) -> "
          f"farmer={action['farmer']} market={action['market']} "
          f"money={me['money']:.0f}")
    return action


def main():
    env = make("kaggriculture", configuration={"episodeSteps": 20}, debug=True)
    env.run([probe, "random"])


if __name__ == "__main__":
    main()
