"""
Analyze a downloaded Kaggle replay to see exactly how a real match played
out, day by day -- the same pattern used locally in Phase 5/6/7's daily
traces, applied to a real leaderboard episode instead of a local run.

Usage:
    python tools/analyze_replay.py replays/94197402.json

If the exact key names below don't match your downloaded file's schema,
run this first to inspect the top-level structure:
    python -c "import json; d = json.load(open('replays/94197402.json')); print(list(d.keys()))"
and share the output -- Kaggle's replay export format can vary slightly
by competition/version.
"""

import json
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/analyze_replay.py <path-to-replay.json>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    steps = data.get("steps", data)  # some exports nest under "steps", some don't

    print(f"Total recorded steps: {len(steps)}\n")
    print(f"{'day':>3} {'hour':>4} {'me_money':>10} {'me_plants':>10} {'me_weeds':>9} {'me_land':>7}  "
          f"{'opp_money':>10} {'opp_plants':>11} {'opp_weeds':>9} {'opp_land':>8}")

    for step in steps:
        # step is usually a list of per-agent dicts, each with an "observation"
        try:
            obs = step[0]["observation"]
        except (KeyError, TypeError, IndexError):
            continue

        hour = obs.get("hour")
        day = obs.get("day")
        if hour != 0:  # once per day only
            continue

        farms = obs.get("farms", [])
        if len(farms) < 2:
            continue

        def summarize(farm):
            tiles = farm.get("tiles", [])
            plants = sum(1 for row in tiles for t in row
                         if isinstance(t, dict) and t.get("kind") == "PLANT")
            weeds = sum(1 for row in tiles for t in row
                        if isinstance(t, dict) and t.get("kind") == "WEED")
            unlocked = len(farm.get("unlocked_quadrants", []))
            return farm.get("money", 0), plants, weeds, unlocked

        me_money, me_plants, me_weeds, me_land = summarize(farms[0])
        opp_money, opp_plants, opp_weeds, opp_land = summarize(farms[1])

        print(f"{day:>3} {hour:>4} {me_money:>10.1f} {me_plants:>10} {me_weeds:>9} {me_land:>7}  "
              f"{opp_money:>10.1f} {opp_plants:>11} {opp_weeds:>9} {opp_land:>8}")

    # Final-turn shed inventory check -- this is the "unsold at game end" question.
    last = steps[-1]
    try:
        me_private = last[0]["observation"]["private"]
        print("\nFinal shed inventory (our agent, unsold at turn 720):")
        for resource, qty in me_private.get("shed", {}).items():
            if qty > 0:
                print(f"  {resource:12s} {qty}")
    except (KeyError, TypeError, IndexError):
        print("\n(Could not read final shed inventory -- check replay structure)")


if __name__ == "__main__":
    main()
