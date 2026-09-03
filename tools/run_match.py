"""
Phase 3 test harness: run main.py against both built-in opponents
("random" and "starter") for a full 720-turn season and print results.

Run from the project root:
    .venv/bin/python tools/run_match.py
"""

from kaggle_environments import make

OPPONENTS = ["random", "starter"]
FULL_SEASON_STEPS = 720


def run_once(opponent, steps=FULL_SEASON_STEPS):
    env = make("kaggriculture", configuration={"episodeSteps": steps}, debug=True)
    env.run(["main.py", opponent])
    final = env.steps[-1]
    return [(s["reward"], s["status"]) for s in final]


def main():
    print(f"Running {FULL_SEASON_STEPS}-step (full season) matches...\n")
    for opponent in OPPONENTS:
        results = run_once(opponent)
        (my_reward, my_status), (opp_reward, opp_status) = results
        outcome = "WIN" if my_reward > opp_reward else (
            "LOSS" if my_reward < opp_reward else "TIE"
        )
        error_flag = " <-- CHECK FOR ERRORS" if "ERROR" in (my_status, opp_status) else ""
        print(f"vs {opponent:8s}  me={my_reward:8.1f} ({my_status})  "
              f"opp={opp_reward:8.1f} ({opp_status})  [{outcome}]{error_flag}")


if __name__ == "__main__":
    main()
