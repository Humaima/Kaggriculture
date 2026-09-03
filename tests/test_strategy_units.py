"""
Unit tests for strategy/state.py. These use small, hand-built obs dicts
(not real episodes) so they run instantly -- this is the whole point of
Phase 2's helper layer.

Run from the project root:
    .venv/bin/python -m pytest tests/test_strategy_units.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy.state import (
    my_farm,
    opp_farm,
    tile_at,
    tiles_of_kind,
    crop_age,
    needs_water_urgently,
    needs_feed_urgently,
    manhattan,
    nearest,
    bfs_path,
    direction_toward,
    quadrant_of,
)


def make_fake_obs(day=0, hour=0, player=0, tiles: list[list[object | None]] | None = None, farmer=(4, 4)):
    if tiles is None:
        tiles = [[None for _ in range(10)] for _ in range(10)]
    farm_a = {"money": 3000.0, "tiles": tiles, "farmer": list(farmer),
              "hands": [], "unlocked_quadrants": ["NW"], "hires_today": 0}
    farm_b = {"money": 3000.0, "tiles": [[None for _ in range(10)] for _ in range(10)],
              "farmer": [4, 4], "hands": [], "unlocked_quadrants": ["NW"],
              "hires_today": 0}
    return {
        "day": day, "hour": hour, "player": player,
        "farms": [farm_a, farm_b] if player == 0 else [farm_b, farm_a],
    }


def test_my_farm_and_opp_farm_pick_correct_index():
    obs = make_fake_obs(player=0)
    assert my_farm(obs)["farmer"] == [4, 4]
    assert opp_farm(obs) is obs["farms"][1]

    obs1 = make_fake_obs(player=1)
    assert my_farm(obs1) is obs1["farms"][1]
    assert opp_farm(obs1) is obs1["farms"][0]


def test_tile_at_out_of_bounds_returns_none():
    obs = make_fake_obs()
    farm = my_farm(obs)
    assert tile_at(farm, -1, 0) is None
    assert tile_at(farm, 0, -1) is None
    assert tile_at(farm, 100, 100) is None
    assert tile_at(farm, 4, 4) is None  # in-bounds, empty tile


def test_tiles_of_kind_finds_empty_locked_and_plant():
    tiles: list[list[object | None]] = [[None] * 10 for _ in range(10)]
    tiles[0][0] = "LOCKED"
    tiles[1][1] = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
                   "watered_today": True, "consecutive_unwatered": 1,
                   "yield_units": 1, "max_lifespan_step": 120,
                   "fertilized_until_day": -1}
    tiles[2][2] = {"kind": "WEED"}
    obs = make_fake_obs(tiles=tiles)
    farm = my_farm(obs)

    assert (0, 0) in tiles_of_kind(farm, "LOCKED")
    assert (1, 1) in tiles_of_kind(farm, "PLANT")
    assert (2, 2) in tiles_of_kind(farm, "WEED")
    # empty tiles: everything except the 3 we set, out of 100 cells
    assert len(tiles_of_kind(farm, "EMPTY")) == 97


def test_crop_age_computes_days_since_planting():
    plant = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 3}
    obs = make_fake_obs(day=7)
    assert crop_age(plant, obs) == 4


def test_needs_water_urgently_true_when_unwatered_today():
    watered = {"kind": "PLANT", "watered_today": True, "consecutive_unwatered": 0}
    unwatered = {"kind": "PLANT", "watered_today": False, "consecutive_unwatered": 1}
    assert needs_water_urgently(watered) is False
    assert needs_water_urgently(unwatered) is True


def test_needs_feed_urgently_checks_animal_present():
    empty_coop = {"kind": "COOP", "animal": None, "fed_today": False,
                  "consecutive_unfed": 1}
    fed_goose = {"kind": "COOP", "animal": "GOOSE", "fed_today": True,
                "consecutive_unfed": 0}
    hungry_goose = {"kind": "COOP", "animal": "GOOSE", "fed_today": False,
                    "consecutive_unfed": 1}
    assert needs_feed_urgently(empty_coop) is False  # no animal placed yet
    assert needs_feed_urgently(fed_goose) is False
    assert needs_feed_urgently(hungry_goose) is True


def test_manhattan_and_nearest():
    assert manhattan((0, 0), (3, 4)) == 7
    targets = [(9, 9), (1, 1), (5, 5)]
    assert nearest((0, 0), targets) == (1, 1)
    assert nearest((0, 0), []) is None


def test_bfs_path_finds_shortest_route_around_open_board():
    obs = make_fake_obs()
    farm = my_farm(obs)
    path = bfs_path(farm, (0, 0), (2, 0))
    assert path == [(1, 0), (2, 0)]

    # locked tiles are passable for movement
    tiles: list[list[object | None]] = [[None] * 10 for _ in range(10)]
    tiles[0][1] = "LOCKED"
    obs2 = make_fake_obs(tiles=tiles)
    farm2 = my_farm(obs2)
    path2 = bfs_path(farm2, (0, 0), (2, 0))
    assert path2 == [(1, 0), (2, 0)]  # still crosses the locked tile


def test_quadrant_of_matches_engine_convention():
    # Confirmed by reading the installed kaggle_environments source
    # (kaggriculture.py: half = board_size // 2, N/S by y, W/E by x).
    assert quadrant_of(0, 0, 10) == "NW"
    assert quadrant_of(4, 4, 10) == "NW"   # farmer's spawn tile
    assert quadrant_of(5, 4, 10) == "NE"   # one step east crosses the boundary
    assert quadrant_of(4, 5, 10) == "SW"   # one step south crosses the boundary
    assert quadrant_of(9, 9, 10) == "SE"


def test_direction_toward_matches_confirmed_game_convention():
    # Confirmed live via kaggle_environments: NORTH decreases y, EAST increases x.
    obs = make_fake_obs()
    farm = my_farm(obs)
    assert direction_toward(farm, (4, 4), (4, 3)) == "NORTH"
    assert direction_toward(farm, (4, 4), (4, 5)) == "SOUTH"
    assert direction_toward(farm, (4, 4), (3, 4)) == "WEST"
    assert direction_toward(farm, (4, 4), (5, 4)) == "EAST"
    assert direction_toward(farm, (4, 4), (4, 4)) is None  # already there


if __name__ == "__main__":
    # Allow running without pytest too: python tests/test_strategy_units.py
    import inspect
    this_module = sys.modules[__name__]
    test_fns = [f for name, f in inspect.getmembers(this_module, inspect.isfunction)
                if name.startswith("test_")]
    passed, failed = 0, 0
    for fn in test_fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
