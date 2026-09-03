"""
Phase 12 flag-validation harness. Toggles strategy.planner's feature flags
in-process (ENABLE_FERTILIZING, ENABLE_ANIMALS, ENABLE_HIRING,
ENABLE_LAND_EXPANSION) and runs the same matchups as tools/self_play.py, to
measure each configuration's effect before deciding whether to flip its
default -- same discipline as every prior phase (Phase 9/10/11): never ship
a measured regression. main.py imports strategy.planner via the normal
module cache, so monkeypatching here reflects exactly what "main.py" does
when kaggle_environments execs it in this same process.

Run from the project root:
    .venv/bin/python tools/validate_flags.py [baseline|fertilizing|animals|animals_land|everything|all]
(defaults to "all")
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kaggle_environments import make
import strategy.planner as planner

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WHEAT_LOOP = os.path.join(PROJECT_ROOT, "agents", "wheat_loop_v1.py")

MATCHUPS = [
    ("starter", "starter", 42),
    ("starter_seed7", "starter", 7),
    ("starter_seed99", "starter", 99),
    ("wheat_loop_v1", WHEAT_LOOP, 42),
]


def run_episode(opponent, seed):
    config = {"episodeSteps": 720, "seed": seed}
    env = make("kaggriculture", configuration=config, debug=True)
    env.run(["main.py", opponent])
    final = env.steps[-1]
    return final[0]["reward"], final[0]["status"], final[1]["reward"], final[1]["status"]


def measure(label):
    print(f"\n=== {label} ===")
    for matchup_label, opponent, seed in MATCHUPS:
        my_reward, my_status, opp_reward, opp_status = run_episode(opponent, seed)
        flag = ""
        if "ERROR" in (my_status, opp_status):
            flag = "  <-- ERROR"
        print(f"  vs {matchup_label:16s} me={my_reward:9.1f} ({my_status})  "
              f"opp={opp_reward:9.1f} ({opp_status})  margin={my_reward - opp_reward:+9.1f}{flag}")


def reset_flags():
    planner.ENABLE_LAND_EXPANSION = False
    planner.ENABLE_HIRING = False
    setattr(planner, "ENABLE_FERTILIZING", False)
    setattr(planner, "ENABLE_LIQUIDATION", True)
    planner.ENABLE_ANIMALS = False


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("baseline", "all"):
        reset_flags()
        measure("baseline (current defaults)")

    if which in ("fertilizing", "all"):
        reset_flags()
        setattr(planner, "ENABLE_FERTILIZING", True)
        measure("ENABLE_FERTILIZING only")

    if which in ("animals", "all"):
        reset_flags()
        planner.ENABLE_HIRING = True
        planner.ENABLE_ANIMALS = True
        measure("ENABLE_HIRING + ENABLE_ANIMALS")

    if which in ("animals_land", "all"):
        reset_flags()
        planner.ENABLE_HIRING = True
        planner.ENABLE_ANIMALS = True
        planner.ENABLE_LAND_EXPANSION = True
        measure("ENABLE_HIRING + ENABLE_ANIMALS + ENABLE_LAND_EXPANSION")

    if which in ("everything", "all"):
        reset_flags()
        planner.ENABLE_HIRING = True
        planner.ENABLE_ANIMALS = True
        planner.ENABLE_LAND_EXPANSION = True
        setattr(planner, "ENABLE_FERTILIZING", True)
        measure("everything on")

    reset_flags()
