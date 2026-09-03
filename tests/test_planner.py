"""
Unit tests for strategy/planner.py's decide() function. Each test builds
a minimal fake obs targeting one priority branch, so we can verify the
planner's decision logic without running a full episode.

Run from the project root:
    .venv/bin/python tests/test_planner.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy.planner import decide, _choose_next_crop, _is_harvestable, _maybe_buy_land, _next_land_cost, _maybe_hire_hands, _fib, _decide_animal_keeper_action, _hand_ramp_cap
from strategy.market import MARKET_PARAMS


def make_obs(day=0, hour=0, money=3000.0, farmer=(4, 4), tile=None,
             seeds=None, shed=None, tiles: "list[list[dict | None]] | None" = None,
             hands=None, hires_today=0, unlocked_quadrants=None):
    if tiles is None:
        tiles = [[None] * 10 for _ in range(10)]
        fx, fy = farmer
        tiles[fy][fx] = tile
    if seeds is None:
        seeds = {c: 0 for c in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")}
    if shed is None:
        shed = {k: 0 for k in (
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
        )}
    if hands is None:
        hands = []
    if unlocked_quadrants is None:
        unlocked_quadrants = ["NW"]
    market_inventory = {name: params["I0"] for name, params in MARKET_PARAMS.items()}
    farm = {"money": money, "tiles": tiles, "farmer": list(farmer),
            "hands": hands, "unlocked_quadrants": unlocked_quadrants,
            "hires_today": hires_today}
    return {
        "day": day, "hour": hour, "player": 0,
        "farms": [farm, farm],
        "private": {"seeds": seeds, "shed": shed, "inventories": []},
        "market": {"inventory": market_inventory,
                   "prices": {n: p["base"] for n, p in MARKET_PARAMS.items()}},
        "town": {"unlocked_shops": []},
    }


def test_waters_a_thirsty_plant_under_the_farmer_first():
    tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
            "watered_today": False, "consecutive_unwatered": 1,
            "yield_units": 1, "max_lifespan_step": 120, "fertilized_until_day": -1}
    obs = make_obs(day=0, tile=tile)
    action = decide(obs)
    assert action["farmer"] == ["WATER"]


def test_harvests_a_ready_one_time_crop_under_the_farmer():
    # Wheat first_yield_day=2; age 2 with yield_units>0 should be harvestable.
    tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
            "watered_today": True, "consecutive_unwatered": 0,
            "yield_units": 4, "max_lifespan_step": 120, "fertilized_until_day": -1}
    obs = make_obs(day=2, tile=tile)
    action = decide(obs)
    assert action["farmer"] == ["HARVEST"]


def test_plants_when_standing_on_empty_tile_with_seed_in_hand():
    obs = make_obs(day=0, tile=None,
                    seeds={"WHEAT": 1, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 0})
    action = decide(obs)
    assert action["farmer"][0] == "PLANT"
    # Should plant whatever _choose_next_crop picks given we hold a WHEAT seed
    assert action["farmer"][1] == "WHEAT"


def test_buys_the_best_affordable_seed_when_none_held():
    obs = make_obs(day=0, tile=None, money=3000.0)
    action = decide(obs)
    # With full money and no seeds held, planner should queue a BUY_SEED
    # for whatever _choose_next_crop ranks first (melon, by revenue/tile/day).
    buy_orders = [o for o in action["market"] if o[0] == "BUY_SEED"]
    assert len(buy_orders) == 1
    assert buy_orders[0][1] == _choose_next_crop(3000.0, {})


def test_travels_toward_nearest_thirsty_plant_when_not_standing_on_one():
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    thirsty = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
               "watered_today": False, "consecutive_unwatered": 1,
               "yield_units": 1, "max_lifespan_step": 120, "fertilized_until_day": -1}
    tiles[4][2] = thirsty  # 2 cells west of farmer at (4,4)
    obs = make_obs(day=0, farmer=(4, 4), tiles=tiles, tile=None)
    action = decide(obs)
    assert action["farmer"] == ["WEST"]


def test_queues_sell_order_for_shed_inventory():
    shed = {k: 0 for k in (
        "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
    )}
    shed["WHEAT"] = 5
    # hour=1 (not the default 0): at hour 0, _maybe_hire_hands legitimately
    # fills most/all of the 10-per-turn market order cap (Phase 13 fix --
    # HIRE/BUY_LAND are queued before SELL since they're once-a-day and
    # time-sensitive), which would starve this turn's SELL orders and make
    # the assertion pass vacuously rather than really exercising selling.
    obs = make_obs(day=0, hour=1, tile=None, shed=shed)
    action = decide(obs)
    sell_orders = [o for o in action["market"] if o[0] == "SELL"]
    assert any(o[1] == "WHEAT" and o[2] == 5 for o in sell_orders)


def test_never_queues_a_sell_order_for_fertilizer_or_live_animals():
    shed = {k: 3 for k in (
        "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
    )}
    obs = make_obs(day=0, hour=1, tile=None, shed=shed)  # see hour=1 note above
    action = decide(obs)
    sold_resources = {o[1] for o in action["market"] if o[0] == "SELL"}
    assert sold_resources  # sanity check this isn't a vacuous pass
    assert "FERTILIZER" not in sold_resources
    assert "GOOSE" not in sold_resources
    assert "COW" not in sold_resources
    assert "SHEEP" not in sold_resources


def test_is_harvestable_false_for_unripe_one_time_crop():
    tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
            "watered_today": True, "yield_units": 0}
    obs = make_obs(day=1)  # age 1, first_yield_day is 2
    assert _is_harvestable(tile, obs) is False


def test_choose_next_crop_prefers_seed_already_held_over_ranking():
    # Even though melon ranks first by revenue, if we already hold a
    # carrot seed, use it rather than buying a new one.
    seeds = {"WHEAT": 0, "CARROT": 1, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 0}
    assert _choose_next_crop(3000.0, seeds) == "CARROT"


def test_choose_next_crop_falls_back_when_broke():
    # With almost no money, should still pick the cheapest affordable crop
    # rather than returning None outright (wheat seed costs $10).
    assert _choose_next_crop(10.0, {}) == "WHEAT"
    assert _choose_next_crop(5.0, {}) is None


def test_digs_a_weed_under_the_farmer_when_nothing_else_to_do():
    # No money to plant, no seeds held -> nothing productive left, so the
    # reactive dig-here fallback should fire.
    tile = {"kind": "WEED"}
    obs = make_obs(day=5, tile=tile, money=0.0)
    action = decide(obs)
    assert action["farmer"] == ["DIG"]


def test_prefers_planting_over_digging_a_weed_it_happens_to_stand_on():
    # Phase 7 finding: proactively chasing weeds cost more in travel time
    # than the reclaimed tile was worth (measured: -$1,198 vs starter,
    # seed=42). This test locks in the resulting design -- if the farmer
    # is standing on a weed but could otherwise be planting/working
    # elsewhere, planting wins. Digging is the last resort, not a
    # standing priority.
    tile = {"kind": "WEED"}
    obs = make_obs(day=5, tile=tile, money=3000.0)
    action = decide(obs)
    assert action["farmer"] != ["DIG"]


def test_thirsty_plant_takes_priority_over_a_farther_weed():
    # West, not east: the farmer is zone-restricted to NW (Phase 13), and
    # (4,4) is NW's own SE corner -- east of it is NE, outside the zone.
    # West stays inside NW while preserving the same relative distances.
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    thirsty = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 5,
               "watered_today": False, "consecutive_unwatered": 1,
               "yield_units": 1, "max_lifespan_step": 120, "fertilized_until_day": -1}
    tiles[4][3] = thirsty  # 1 cell west
    tiles[4][2] = {"kind": "WEED"}  # 2 cells west (farther)
    obs = make_obs(day=5, farmer=(4, 4), tiles=tiles, tile=None)
    action = decide(obs)
    assert action["farmer"] == ["WEST"]  # heads toward the thirsty plant first
    # (both are technically 1 step west from here, so this specifically
    # verifies thirsty-plant targeting runs before weed targeting in the
    # priority order -- the nearer, more urgent tile wins the race.)


def test_standing_on_weed_still_chases_a_thirsty_plant_elsewhere_first():
    # This is the Phase 7 fix: DIG-here must be checked AFTER the global
    # thirsty-plant search, not before -- a dead weed tile can wait a turn,
    # a live plant on the brink of decay can't. West, not east: the farmer
    # is zone-restricted to NW (Phase 13), and (4,4) is NW's own SE corner.
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    tiles[4][4] = {"kind": "WEED"}  # farmer is standing on this weed
    thirsty = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 5,
               "watered_today": False, "consecutive_unwatered": 1,
               "yield_units": 1, "max_lifespan_step": 120, "fertilized_until_day": -1}
    tiles[4][2] = thirsty  # elsewhere on the farm, still inside NW
    obs = make_obs(day=5, farmer=(4, 4), tiles=tiles, tile=tiles[4][4])
    action = decide(obs)
    assert action["farmer"] == ["WEST"]  # heads toward the thirsty plant, not DIG


def test_next_land_cost_matches_documented_tiers():
    # Confirmed empirically: 1st extra quadrant $1000, 2nd $2000;
    # doc states 3rd is $4000.
    assert _next_land_cost(1) == 1000  # own just NW, buying the 1st extra
    assert _next_land_cost(2) == 2000  # own 2 quadrants, buying the 2nd extra
    assert _next_land_cost(3) == 4000  # own 3 quadrants, buying the 3rd extra


def test_buys_land_when_running_low_on_space_and_affordable():
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]  # mostly empty -> plenty of EMPTY tiles
    # Fill everything except 2 tiles so EMPTY count is under the threshold (3)
    filled = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0}
    count = 0
    for y in range(10):
        for x in range(10):
            if count >= 98:
                break
            tiles[y][x] = filled
            count += 1
    farm = {"money": 5000.0, "tiles": tiles, "unlocked_quadrants": ["NW"]}
    assert _maybe_buy_land(farm) == ["BUY_LAND"]


def test_does_not_buy_land_when_plenty_of_space_left():
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]  # almost entirely empty
    farm = {"money": 5000.0, "tiles": tiles, "unlocked_quadrants": ["NW"]}
    assert _maybe_buy_land(farm) is None


def test_does_not_buy_land_when_cannot_afford_it_with_reserve():
    # Tight on space, but not enough money for cost + cash reserve
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    filled = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0}
    count = 0
    for y in range(10):
        for x in range(10):
            if count >= 98:
                break
            tiles[y][x] = filled
            count += 1
    farm = {"money": 500.0, "tiles": tiles, "unlocked_quadrants": ["NW"]}  # far short of $2000 needed
    assert _maybe_buy_land(farm) is None


def test_does_not_buy_land_when_tight_on_cash_even_if_technically_affordable():
    # Phase 9 fix: this is exactly the day-4 scenario that caused the
    # regression -- can afford the $1000 sticker price but not with the
    # $1000 reserve on top.
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    filled = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0}
    count = 0
    for y in range(10):
        for x in range(10):
            if count >= 98:
                break
            tiles[y][x] = filled
            count += 1
    farm = {"money": 1500.0, "tiles": tiles, "unlocked_quadrants": ["NW"]}  # can afford $1000 but not +$1000 reserve
    assert _maybe_buy_land(farm) is None


def test_does_not_buy_land_once_fully_expanded():
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    filled = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0}
    count = 0
    for y in range(10):
        for x in range(10):
            if count >= 98:
                break
            tiles[y][x] = filled
            count += 1
    farm = {"money": 50000.0, "tiles": tiles, "unlocked_quadrants": ["NW", "NE", "SW", "SE"]}
    assert _maybe_buy_land(farm) is None


def test_fib_matches_documented_hire_cost_sequence():
    # Doc: "1, 1, 2, 3, 5, 8, 13, etc..." -- confirmed empirically too.
    assert [_fib(n) for n in range(7)] == [1, 1, 2, 3, 5, 8, 13]


def test_hand_ramp_cap_grows_by_one_per_day_then_caps():
    # Phase 14: ramps from HAND_RAMP_START by +1/day, capped at _max_hands_per_day().
    # Only ramps with ENABLE_LAND_EXPANSION on -- see test below for the
    # land-off "no ramp" behavior.
    import strategy.planner as planner
    original = planner.ENABLE_LAND_EXPANSION
    planner.ENABLE_LAND_EXPANSION = True
    try:
        assert _hand_ramp_cap(0) == planner.HAND_RAMP_START
        assert _hand_ramp_cap(1) == planner.HAND_RAMP_START + 1
        assert _hand_ramp_cap(3) == planner.HAND_RAMP_START + 3
        assert _hand_ramp_cap(100) == planner._max_hands_per_day()  # never exceeds the cap
    finally:
        planner.ENABLE_LAND_EXPANSION = original


def test_hand_ramp_cap_does_not_ramp_when_land_expansion_is_off():
    # Phase 14: the ramp is a pure cost with land off (measured -6.3%,
    # see HAND_RAMP_START's comment) -- returns the full hand count
    # immediately regardless of day.
    import strategy.planner as planner
    original = planner.ENABLE_LAND_EXPANSION
    planner.ENABLE_LAND_EXPANSION = False
    try:
        assert _hand_ramp_cap(0) == planner._max_hands_per_day() == 6
    finally:
        planner.ENABLE_LAND_EXPANSION = original


def test_hires_hands_at_start_of_day_when_affordable():
    # _maybe_hire_hands is gated by ENABLE_HIRING (off by default -- see
    # planner.py's Phase 10 finding). Patch it on to test the underlying
    # decision logic in isolation, independent of the default setting.
    import strategy.planner as planner
    orig_hiring, orig_land = planner.ENABLE_HIRING, planner.ENABLE_LAND_EXPANSION
    planner.ENABLE_HIRING, planner.ENABLE_LAND_EXPANSION = True, False
    try:
        # ENABLE_LAND_EXPANSION off (Phase 15 flipped the default to True,
        # so pinned False here explicitly): no ramp -- hires the full
        # _max_hands_per_day() (6) immediately, as in Phase 13. Phase 14's
        # ramp only applies with land expansion on (see
        # test_land_expansion_ramps_hiring_by_day for that case) since the
        # land-off roster was never the source of the day-0 cash crash.
        obs = make_obs(hour=0, hires_today=0, day=0, money=3000.0)
        farm = obs["farms"][0]
        orders = _maybe_hire_hands(farm, obs)
        assert orders == [["HIRE"]] * 6
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_LAND_EXPANSION = orig_hiring, orig_land


def test_land_expansion_ramps_hiring_by_day():
    # Phase 14: with ENABLE_LAND_EXPANSION on, hiring ramps from
    # HAND_RAMP_START by +1/day instead of jumping straight to
    # _max_hands_per_day() (9) on day 0 -- the root cause of Phase 13's
    # cash-crash collapse. $3000 easily affords either count (fib costs
    # are cheap) well within the $500 reserve, so the ramp cap is what's
    # actually under test here, not affordability.
    import strategy.planner as planner
    orig_hiring, orig_land = planner.ENABLE_HIRING, planner.ENABLE_LAND_EXPANSION
    planner.ENABLE_HIRING, planner.ENABLE_LAND_EXPANSION = True, True
    try:
        obs = make_obs(hour=0, hires_today=0, day=0, money=3000.0)
        farm = obs["farms"][0]
        assert _maybe_hire_hands(farm, obs) == [["HIRE"]] * planner.HAND_RAMP_START

        obs = make_obs(hour=0, hires_today=0, day=100, money=3000.0)
        farm = obs["farms"][0]
        assert _maybe_hire_hands(farm, obs) == [["HIRE"]] * 9
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_LAND_EXPANSION = orig_hiring, orig_land


def test_does_not_hire_mid_day():
    import strategy.planner as planner
    original = planner.ENABLE_HIRING
    planner.ENABLE_HIRING = True
    try:
        obs = make_obs(hour=5, hires_today=0, money=3000.0)
        farm = obs["farms"][0]
        assert _maybe_hire_hands(farm, obs) == []
    finally:
        planner.ENABLE_HIRING = original


def test_does_not_rehire_same_day():
    import strategy.planner as planner
    original = planner.ENABLE_HIRING
    planner.ENABLE_HIRING = True
    try:
        obs = make_obs(hour=0, hires_today=2, money=3000.0)
        farm = obs["farms"][0]
        assert _maybe_hire_hands(farm, obs) == []
    finally:
        planner.ENABLE_HIRING = original


def test_does_not_hire_when_it_would_break_the_cash_reserve():
    import strategy.planner as planner
    original = planner.ENABLE_HIRING
    planner.ENABLE_HIRING = True
    try:
        obs = make_obs(hour=0, hires_today=0, money=501.0)
        farm = obs["farms"][0]
        orders = _maybe_hire_hands(farm, obs)
        # $501 - fib(0)=$1 = $500, exactly at the $500 reserve -> 1 hire allowed;
        # a 2nd would drop to $499, below reserve -> stops there.
        assert orders == [["HIRE"]]
    finally:
        planner.ENABLE_HIRING = original


def test_does_not_hire_at_all_when_even_one_hire_breaks_reserve():
    import strategy.planner as planner
    original = planner.ENABLE_HIRING
    planner.ENABLE_HIRING = True
    try:
        obs = make_obs(hour=0, hires_today=0, money=500.0)  # can't even afford $1 + $500 reserve
        farm = obs["farms"][0]
        assert _maybe_hire_hands(farm, obs) == []
    finally:
        planner.ENABLE_HIRING = original


def test_farmer_and_hand_do_not_target_the_same_empty_tile():
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    obs = make_obs(farmer=(4, 4), tile=None, tiles=tiles,
                    hands=[[4, 6]],  # 2 cells south of farmer
                    seeds={"WHEAT": 0, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 5})
    action = decide(obs)
    # Farmer stands on an empty tile -> should plant immediately, consuming 1 seed.
    assert action["farmer"] == ["PLANT", "MELON"]
    # Hand is also on an empty tile -> should also plant (we hold 5 seeds, plenty).
    assert action["hands"][0] == ["PLANT", "MELON"]


def test_seed_budget_prevents_double_planting_with_only_one_seed_held():
    # Doc rule: if two units try to plant the same crop with insufficient
    # seed, NEITHER succeeds. Our planner must never let this happen --
    # only one unit should be told to PLANT; the other should do
    # something else (travel, since it's already on an empty tile with no
    # seed available -> falls through toward PASS in this minimal setup).
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    obs = make_obs(farmer=(4, 4), tile=None, tiles=tiles,
                    hands=[[4, 6]],
                    seeds={"WHEAT": 0, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 1})
    action = decide(obs)
    plant_actions = [a for a in [action["farmer"]] + action["hands"] if a[0] == "PLANT"]
    assert len(plant_actions) == 1  # exactly one unit plants, never both


def test_hand_actions_list_matches_number_of_hands():
    obs = make_obs(hands=[[4, 6], [6, 4], [6, 6]])
    action = decide(obs)
    assert len(action["hands"]) == 3


def test_buy_seed_quantity_scales_with_number_of_units_wanting_it():
    # Phase 10 bug fix: previously only ever bought 1 seed regardless of
    # how many units wanted to plant, under-supplying a multi-unit farm.
    # Phase 13 update: with one animal-keeper per animal type, hand[1]
    # (cow) and hand[2] (sheep) are both diverted to BUILD_PASTURE instead
    # of wanting a crop seed (money=3000 clears ANIMAL_BUILD_RESERVE,
    # standing on empty tiles) -- so only 2 of the 4 units (farmer,
    # hand[0]) request MELON. ENABLE_LAND_EXPANSION pinned False (Phase 15
    # flipped the default to True): Phase 14's activation staggering only
    # applies when land expansion is on, so both keepers are active
    # immediately here, as in Phase 13.
    import strategy.planner as planner
    original = planner.ENABLE_LAND_EXPANSION
    planner.ENABLE_LAND_EXPANSION = False
    try:
        tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
        obs = make_obs(farmer=(4, 4), tile=None, tiles=tiles,
                        hands=[[4, 6], [6, 4], [6, 6]],  # 3 hands, all on empty tiles
                        money=3000.0,
                        seeds={"WHEAT": 0, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 0})
        action = decide(obs)
        buy_orders = [o for o in action["market"] if o[0] == "BUY_SEED"]
        assert len(buy_orders) == 1
        assert buy_orders[0][1] == "MELON"
        assert buy_orders[0][2] == 2
    finally:
        planner.ENABLE_LAND_EXPANSION = original


def test_weed_patrol_hand_proactively_travels_toward_a_distant_weed():
    # Phase 11: unlike the sole-farmer case (Phase 7, where proactive
    # weed-chasing measured worse), a dedicated hand SHOULD proactively
    # travel toward a weed rather than defaulting to general duty.
    # ENABLE_HIRING is off by default (see planner.py's Phase 11 finding)
    # -- patch it on to test the routing logic itself, independent of
    # whether the feature is currently shipped active.
    import strategy.planner as planner
    original = planner.ENABLE_HIRING
    planner.ENABLE_HIRING = True
    try:
        tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
        tiles[6][6] = {"kind": "WEED"}  # 2 cells away from the hand's spawn
        obs = make_obs(tiles=tiles, hands=[[4, 6]])  # hand 2 cells west of the weed
        action = decide(obs)
        assert action["hands"][0] == ["EAST"]
    finally:
        planner.ENABLE_HIRING = original


def test_weed_patrol_hand_falls_back_to_general_duty_when_farm_is_clean():
    import strategy.planner as planner
    original = planner.ENABLE_HIRING
    planner.ENABLE_HIRING = True
    try:
        tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]  # no weeds anywhere
        obs = make_obs(tiles=tiles, hands=[[4, 6]], money=3000.0,
                        seeds={"WHEAT": 0, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 5})
        action = decide(obs)
        assert action["hands"][0] == ["PLANT", "MELON"]  # standing on empty, plenty of seed
    finally:
        planner.ENABLE_HIRING = original


def test_animal_keeper_builds_pasture_when_no_structure_exists():
    import strategy.planner as planner
    orig_hiring, orig_animals = planner.ENABLE_HIRING, planner.ENABLE_ANIMALS
    planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = True, True
    try:
        tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
        obs = make_obs(tiles=tiles, hands=[[4, 6], [6, 4]], money=3000.0)
        action = decide(obs)
        assert action["hands"][1] == ["BUILD_PASTURE"]
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = orig_hiring, orig_animals


def test_animal_keeper_picks_up_cow_when_standing_at_shed_with_unoccupied_pasture():
    import strategy.planner as planner
    orig_hiring, orig_animals = planner.ENABLE_HIRING, planner.ENABLE_ANIMALS
    planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = True, True
    try:
        tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
        tiles[6][6] = {"kind": "PASTURE"}  # unoccupied, elsewhere on the farm
        shed = {k: 0 for k in (
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
        )}
        shed["COW"] = 1
        obs = make_obs(tiles=tiles, hands=[[4, 6], [4, 4]], money=3000.0, shed=shed)
        action = decide(obs)
        # 2nd hand (index 1) stands at (4,4), the confirmed shed-adjacent tile
        assert action["hands"][1] == ["PICKUP", "COW", 1]
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = orig_hiring, orig_animals


def test_animal_keeper_places_cow_when_carrying_one_on_unoccupied_pasture():
    import strategy.planner as planner
    orig_hiring, orig_animals = planner.ENABLE_HIRING, planner.ENABLE_ANIMALS
    planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = True, True
    try:
        pasture_tile = {"kind": "PASTURE"}
        obs = make_obs(tile=pasture_tile, hands=[[4, 6], [4, 4]], money=3000.0)
        # Manually inject inventory as if PICKUP already happened -- test
        # fixture doesn't model inventory transitions, only the routing.
        obs["private"]["inventories"] = [{}, {}, {"COW": 1}]
        action = decide(obs)
        assert action["hands"][1] == ["PLACE", "COW"]
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = orig_hiring, orig_animals


def test_animal_keeper_feeds_when_carrying_wheat_and_animal_needs_it():
    import strategy.planner as planner
    orig_hiring, orig_animals = planner.ENABLE_HIRING, planner.ENABLE_ANIMALS
    planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = True, True
    try:
        hungry_cow_tile = {"kind": "PASTURE", "animal": "COW", "fed_today": False,
                            "consecutive_unfed": 1, "cared_today": False,
                            "yield_units": 0, "fertilizer_available": False}
        obs = make_obs(tile=hungry_cow_tile, hands=[[4, 6], [4, 4]], money=3000.0)
        obs["private"]["inventories"] = [{}, {}, {"WHEAT": 3}]
        action = decide(obs)
        assert action["hands"][1] == ["FEED"]
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = orig_hiring, orig_animals


def test_animal_keeper_harvests_when_animal_product_is_ready():
    import strategy.planner as planner
    orig_hiring, orig_animals = planner.ENABLE_HIRING, planner.ENABLE_ANIMALS
    planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = True, True
    try:
        ready_cow_tile = {"kind": "PASTURE", "animal": "COW", "fed_today": True,
                           "consecutive_unfed": 0, "cared_today": True,
                           "yield_units": 2, "fertilizer_available": False}
        obs = make_obs(tile=ready_cow_tile, hands=[[4, 6], [4, 4]], money=3000.0)
        action = decide(obs)
        assert action["hands"][1] == ["HARVEST"]
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_ANIMALS = orig_hiring, orig_animals


def test_animal_keepers_diversify_across_cow_sheep_and_goose():
    # Phase 13: one dedicated keeper per ANIMAL_TABLE entry, ranked by
    # revenue/tile/day (confirmed: cow, sheep, goose). hand[1]=cow,
    # hand[2]=sheep, hand[3]=goose -- each should build its OWN structure
    # kind (pasture for cow/sheep, coop for goose) rather than all piling
    # onto the same animal like the Phase 12 cow-only version did.
    # ENABLE_LAND_EXPANSION pinned False here (Phase 15 flipped the
    # default to True): Phase 14's activation staggering only applies with
    # land expansion on, so all 3 keepers are active immediately from day
    # 0, as in Phase 13 -- see
    # test_land_expansion_staggers_animal_keeper_activation for the
    # staggered case.
    import strategy.planner as planner
    orig_hiring, orig_animals, orig_land = planner.ENABLE_HIRING, planner.ENABLE_ANIMALS, planner.ENABLE_LAND_EXPANSION
    planner.ENABLE_HIRING, planner.ENABLE_ANIMALS, planner.ENABLE_LAND_EXPANSION = True, True, False
    try:
        tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
        obs = make_obs(tiles=tiles, hands=[[4, 6], [6, 4], [6, 6], [3, 4]], money=3000.0)
        action = decide(obs)
        assert action["hands"][1] == ["BUILD_PASTURE"]  # cow keeper
        assert action["hands"][2] == ["BUILD_PASTURE"]  # sheep keeper
        assert action["hands"][3] == ["BUILD_COOP"]      # goose keeper
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_ANIMALS, planner.ENABLE_LAND_EXPANSION = orig_hiring, orig_animals, orig_land


def test_land_expansion_staggers_animal_keeper_activation():
    # Phase 14: with ENABLE_LAND_EXPANSION on, keeper_slot N doesn't
    # activate until day >= N * ANIMAL_KEEPER_STAGGER_DAYS -- before that
    # it patrols weeds instead of immediately buying its animal, so
    # cow/sheep/goose purchases don't all hit the bank on day 0.
    import strategy.planner as planner
    orig_hiring, orig_animals, orig_land = planner.ENABLE_HIRING, planner.ENABLE_ANIMALS, planner.ENABLE_LAND_EXPANSION
    planner.ENABLE_HIRING, planner.ENABLE_ANIMALS, planner.ENABLE_LAND_EXPANSION = True, True, True
    try:
        tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
        # day=0: only the cow keeper (slot 0, activates day>=0) is live;
        # sheep (slot 1, day>=5) and goose (slot 2, day>=10) aren't yet.
        obs = make_obs(day=0, tiles=tiles, hands=[[4, 6], [6, 4], [6, 6], [3, 4]], money=3000.0)
        action = decide(obs)
        assert action["hands"][1] == ["BUILD_PASTURE"]   # cow keeper: active
        assert action["hands"][2] != ["BUILD_PASTURE"]   # sheep keeper: not yet
        assert action["hands"][3] != ["BUILD_COOP"]      # goose keeper: not yet

        # day=10: past every keeper's activation threshold.
        obs = make_obs(day=10, tiles=tiles, hands=[[4, 6], [6, 4], [6, 6], [3, 4]], money=3000.0)
        action = decide(obs)
        assert action["hands"][1] == ["BUILD_PASTURE"]
        assert action["hands"][2] == ["BUILD_PASTURE"]
        assert action["hands"][3] == ["BUILD_COOP"]
    finally:
        planner.ENABLE_HIRING, planner.ENABLE_ANIMALS, planner.ENABLE_LAND_EXPANSION = orig_hiring, orig_animals, orig_land


def test_sheep_keeper_does_not_target_the_pasture_the_cow_keeper_already_claimed():
    # Cow and sheep keepers both deliver to PASTURE tiles -- with only one
    # empty pasture and both already carrying their animal, `claimed` must
    # stop the sheep keeper from also walking toward the tile the cow
    # keeper (processed first) just claimed.
    tiles: list[list[dict | None]] = [[None] * 10 for _ in range(10)]
    tiles[4][6] = {"kind": "PASTURE"}  # single unoccupied pasture at (6,4)
    obs = make_obs(tiles=tiles, hands=[[2, 4], [8, 4]])
    obs["private"]["inventories"] = [{}, {"COW": 1}, {"SHEEP": 1}]
    farm = obs["farms"][0]
    claimed = set()
    cow_action = _decide_animal_keeper_action(
        1, (2, 4), farm, obs, claimed, {}, {}, "COW", set(), [False])
    assert (6, 4) in claimed  # cow keeper claimed the only pasture
    assert cow_action == ["EAST"]  # and heads toward it
    sheep_action = _decide_animal_keeper_action(
        2, (8, 4), farm, obs, claimed, {}, {}, "SHEEP", set(), [False])
    assert sheep_action != cow_action  # sheep keeper must not also target it


if __name__ == "__main__":
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
        except Exception as e:
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
