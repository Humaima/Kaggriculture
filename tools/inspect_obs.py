"""
Phase 2 exploration tool: run a short episode with a probe agent that
captures the raw obs dict at a handful of checkpoints (start of day 0,
mid-game, etc.) and prints it. This is throwaway/dev tooling -- it never
ships in the submission.

Run from the project root:
    .venv/bin/python tools/inspect_obs.py
"""

import json
from kaggle_environments import make

# (day, hour) checkpoints to capture. hour=0 is the first turn of that day.
CHECKPOINTS = {(0, 0), (0, 3), (2, 0)}

captured = []


def probe_agent(obs):
    if (obs["day"], obs["hour"]) in CHECKPOINTS:
        captured.append(json.loads(json.dumps(obs, default=str)))

    # Buy + plant a wheat seed on turn 0, then water it once, so later
    # checkpoints show us a real PLANT tile dict instead of an empty farm.
    if obs["step"] == 0:
        return {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}
    if obs["step"] == 1:
        return {"farmer": ["PLANT", "WHEAT"], "hands": [], "market": []}
    if obs["step"] == 2:
        return {"farmer": ["WATER"], "hands": [], "market": []}
    return {"farmer": ["PASS"], "hands": [], "market": []}


def main():
    env = make("kaggriculture", configuration={"episodeSteps": 60}, debug=True)
    env.run([probe_agent, "random"])

    for obs in captured:
        print(f"\n=== day={obs['day']} hour={obs['hour']} ===")
        print("top-level keys:", sorted(obs.keys()))
        print("farm keys:", sorted(obs["farms"][obs["player"]].keys()))
        print("farmer position:", obs["farms"][obs["player"]]["farmer"])
        print("unlocked_quadrants:", obs["farms"][obs["player"]]["unlocked_quadrants"])
        print("private keys:", sorted(obs["private"].keys()))
        print("private.shed:", obs["private"]["shed"])
        print("private.seeds:", obs["private"]["seeds"])
        print("market keys:", sorted(obs["market"].keys()))
        print("market.prices (sample):",
              {k: obs["market"]["prices"][k] for k in list(obs["market"]["prices"])[:4]})
        print("town:", obs["town"])
        fx, fy = obs["farms"][obs["player"]]["farmer"]
        tile = obs["farms"][obs["player"]]["tiles"][fy][fx]
        print(f"tile under farmer at ({fx},{fy}):", tile)


if __name__ == "__main__":
    main()
