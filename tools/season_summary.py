"""
Quick manual probe: run a full 720-step season against 'starter' and print
a one-line-per-day summary (money, plant count, weed count) so you can
eyeball how the planner's economy and tile upkeep trend over a season.

Run from the project root:
    .venv/bin/python tools/season_summary.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kaggle_environments import make


def main():
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
    env.run(["main.py", "starter"])

    for step in env.steps:
        obs = step[0]["observation"]
        if obs["hour"] == 0:
            me = obs["farms"][0]
            weeds = sum(1 for row in me["tiles"] for t in row
                        if isinstance(t, dict) and t.get("kind") == "WEED")
            plants = sum(1 for row in me["tiles"] for t in row
                         if isinstance(t, dict) and t.get("kind") == "PLANT")
            print(f"day={obs['day']:2d}  money={me['money']:8.1f}  "
                  f"plants={plants:2d}  weeds={weeds:2d}")


if __name__ == "__main__":
    main()
