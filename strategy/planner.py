"""
Phase 5 planner (Phase 7: weed clearing; Phase 9: land expansion,
disabled; Phase 10: hired hands + land expansion re-enabled together;
Phase 13: 6-hand roster with one dedicated keeper per animal type -- a
measured win, kept on; zone-based land expansion built and re-tested,
still a net loss locally, root cause diagnosed as an onboarding-pace
problem, not coordination; Phase 14: staggered hiring/animal ramp-up fixed
that root cause (no more boom-bust cash crash) but land expansion was
still a net loss vs `starter` locally; Phase 15: real leaderboard replays
(not local self-play) showed an actual opponent profiting from expanding
land against us, so land expansion is re-enabled to test against real
opponents despite the local loss. See ENABLE_LAND_EXPANSION's comment for
the full evidence and numbers).

Priority order, applied per-unit (farmer, then each hand in turn):
  1. Protect assets: water the tile the unit is standing on if urgent.
  2. Harvest if standing on a ready plant.
  3. Travel toward the nearest tile that urgently needs water
     (excluding tiles already claimed by another unit this turn).
  4. Travel toward the nearest harvestable tile (same exclusion).
  5. Plant on an empty tile if standing on one and a seed is available
     in a shared per-turn seed budget (see note below).
  6. Travel toward the nearest empty tile to plant on.
  7. Dig up a weed if standing on one and nothing more productive to do.
  8. PASS.

Design note on weeds (Phase 7 finding): proactively traveling toward
weeds measured worse than doing nothing (-$1,198 vs starter, seed=42).
This reactive-only version digs only when a unit is already standing on
a weed, never routes there specifically.

Design note on land + hands (Phase 9 -> Phase 10): BUY_LAND alone (single
farmer) measured as a net negative twice (-$1,996 and -$1,560 vs starter,
seed=42) because one farmer can't physically cover the extra tiles fast
enough -- the new land just sat mostly empty, accumulating weeds. HIRE
(confirmed empirically: `["HIRE"]`, no args, Fibonacci cost 1,1,2,3,5,8...
that resets daily, hands disappear at day end and must be rehired) adds
real parallel labor. Both are re-enabled together here, since land without
labor to work it was the measured problem, not land itself.

Critical constraint (from the doc, easy to violate): "If you try to plant
too many in a specific turn, none are planted" -- if two units both issue
PLANT MELON in the same turn but only 1 seed is held, BOTH actions are
wasted, not just one. To avoid this, decide() tracks a shared seed_budget
across all units for the turn, decremented as each unit is assigned to
plant, so at most as many units are told to PLANT a given crop as we
actually hold seed for.

Market orders (sell shed inventory, buy seeds, buy land, hire hands) are
queued every turn regardless of unit movement, since market orders are a
separate action slot from each unit's single action.

"""

from strategy.state import (
    my_farm,
    tiles_of_kind,
    crop_age,
    needs_water_urgently,
    needs_feed_urgently,
    nearest,
    direction_toward,
    quadrant_of,
)
from strategy.crops import (
    CROP_TABLE,
    ONE_TIME,
    ONGOING,
    is_scheduled_production_day,
    best_crop_by_revenue_per_tile_day,
)
from strategy.animals import (
    ANIMAL_TABLE,
    is_structure_unoccupied,
    is_structure_occupied,
    is_ready_to_harvest_animal,
    needs_care,
    fertilizer_ready,
    best_animal_by_revenue_per_tile_day,
)
from strategy.market import price, estimate_sell_proceeds

# Don't let a batch sell push the price below this fraction of base --
# beyond this point we'd rather carry inventory another turn than dump it.
MIN_SELL_PRICE_FRACTION = 0.5
MAX_SELL_PER_ORDER = 20  # keep individual sell orders modest
MAX_MARKET_ORDERS_PER_TURN = 10  # matches maxMarketOrdersPerTurn's documented
# default; the engine silently drops orders past this per turn, so decide()
# queues HIRE/BUY_LAND/BUY_SEED/BUY_ANIMAL/BUY_PRODUCT first (time-sensitive,
# once-a-day decisions) and trims SELL orders to whatever room is left,
# rather than risk the engine dropping something more important (Phase 13
# fix -- previously SELL was queued first).

ALL_QUADRANTS = 4
ZONE_ORDER = ["NE", "SW", "SE"]  # the engine's actual land-purchase order,
# confirmed by reading kaggle_environments' kaggriculture.py (LAND_ORDER) --
# used to assign each newly bought quadrant its own dedicated zone-farmer
# hand (see decide()).
MAX_QUADRANTS_TO_BUY = ALL_QUADRANTS  # Phase 13: Phases 9-11 found land
# expansion lost money because a handful of undifferentiated hands couldn't
# physically cover it (see ENABLE_LAND_EXPANSION history below). Phase 13
# adds dedicated zone-farmers (one per quadrant, see ZONE_ORDER) instead of
# just more undifferentiated hands -- re-test the full cap with that in
# place before assuming it's still unprofitable.
LAND_BUY_EMPTY_TILE_THRESHOLD = 3  # only expand once genuinely tight on space
LAND_BUY_CASH_RESERVE = 1000  # keep this much spare after buying, for seeds
# Phase 9-11 finding: HIRE + BUY_LAND were fully implemented (mechanically
# correct: seed-buying scales with unit count, no double-planting, no
# duplicate travel targets -- all unit-tested) and measured across THREE
# different seeds (42, 7, 99) against `starter`. Every configuration of
# undifferentiated hands + land lost money vs a plain single farmer,
# ~9-20% depending on how much land/labor was added (see git history /
# PROJECT_STATUS.md Phase 10-11 for the exact numbers) -- more land and
# more hands genuinely added more coverage, but "everyone follows the same
# nearest-target priority list" wasn't smart enough to turn that coverage
# into profit. Phase 13 replaces that undifferentiated scaling with
# dedicated zone-farmers (one hand assigned per quadrant, see ZONE_ORDER
# and _decide_unit_action's `zone` param) specifically to fix the
# coordination problem rather than just add more labor to it.
ENABLE_LAND_EXPANSION = True  # Phase 15: re-enabled despite Phases 9-14's
# consistent LOCAL losses against `starter` (8 measurements, most recently
# Phase 14's zone-farmers+staggered-onboarding at -60% to -64% vs land off:
#   seed=42: land off $31,187  vs  zone-farmers+staggered $11,168  (-64.2%)
#   seed=7:  land off $30,723  vs  zone-farmers+staggered $11,686  (-62.0%)
#   seed=99: land off $31,445  vs  zone-farmers+staggered $12,446  (-60.4%)
# -- because REAL leaderboard replays tell a different story than local
# self-play against the scripted `starter` bot. Pulled two actual episode
# replays (95098360, 95029677 -- kaggle competitions replay) and traced
# them with tools/analyze_replay.py: our submitted agent's land stayed at
# 1 quadrant for all 720 turns in BOTH real matches (ENABLE_LAND_EXPANSION
# was off in both of those historical submissions too), while the REAL
# opponent expanded to 2 quadrants around day 17-19 and pulled ahead --
# in episode 95029677, day 29: us $14,218 (land=1) vs opponent $28,399
# (land=2). Real opponents evidently play differently enough from
# `starter` that expansion pays off against them even though it measured
# as a loss locally. This directly matches the doc's own caveat: "real-
# world leaderboard performance is not guaranteed to match local self-play
# against starter." Phase 14's zone-farmer + staggered-onboarding
# infrastructure (see _max_hands_per_day, HAND_RAMP_START,
# ANIMAL_KEEPER_STAGGER_DAYS below) already fixed the worst local failure
# mode (the day-0 cash-crash boom-bust cycle), so this re-enables land
# expansion on top of that fix specifically to test it against real
# opponents rather than only the scripted bot. Revert to False if a real
# submission with this on measures worse than the land-off baseline.

def _max_hands_per_day():
    """
    Phase 13: 1 weed-patrol + 3 animal-keepers (one per ANIMAL_TABLE
    entry: cow, sheep, goose, all farm-wide) + 3 zone-farmers (one per
    ZONE_ORDER quadrant, only hired when ENABLE_LAND_EXPANSION is on) + 2
    general-duty hands. Was 2 (1 weed-patrol + 1 animal-keeper, cow only)
    through Phase 12. A function (not a frozen module constant) so it
    always reflects ENABLE_LAND_EXPANSION's current value, including when
    tests patch it at runtime.

    The zone-farmer count is gated by ENABLE_LAND_EXPANSION rather than
    always hired: measured hiring all 3 anyway (falling back to farm-wide
    duty when their quadrant isn't unlocked) with land OFF, and it
    actively hurt -- 3 extra hands crowding the same single NW quadrant
    with nothing new to work, $27,443 vs the 6-hand number below (-4.6%).
    Gating them restores the 6-hand roster's measured win, land off, on
    all 3 seeds (numbers below include the market-order-priority fix
    documented on MAX_MARKET_ORDERS_PER_TURN, which improved this
    baseline further from an earlier $28,779/$28,270/$29,291):
      seed=42: baseline $26,688  vs  6-hand roster $31,187  (+16.9%)
      seed=7:  baseline $26,608  vs  6-hand roster $30,723  (+15.5%)
      seed=99: baseline $26,688  vs  6-hand roster $31,445  (+17.8%)
    See ENABLE_LAND_EXPANSION's comment for the 9-hand, zone-farmer result
    and ANIMAL_KEEPER_STAGGER_DAYS below for the Phase 14 fix.
    """
    return 6 + (len(ZONE_ORDER) if ENABLE_LAND_EXPANSION else 0)


HIRE_CASH_RESERVE = 500  # keep this much spare after hiring, for seeds
ENABLE_HIRING = True  # Phase 12: enabled -- see finding below

HAND_RAMP_START = 1  # Phase 14: hire at most this many hands on day 0,
# ramping by +1/day (see _maybe_hire_hands) until _max_hands_per_day() is
# reached. Root cause of Phase 13's zone-farmer collapse: jumping straight
# to 9 hands (plus 3 simultaneous animal purchases, see
# ANIMAL_KEEPER_STAGGER_DAYS) on day 0 bled the $3,000 starting cash to
# under $20 before any harvest income arrived, dropping below
# HIRE_CASH_RESERVE and permanently blocking rehiring into a recurring
# boom-bust cycle. Ramping gives crops/animals time to start producing
# before labor costs scale up. With this ramp, day 0 hires only the
# single highest-priority role (weed-patrol); the animal-keepers,
# zone-farmers, and general-duty hands (later slots in decide()'s
# dispatch) naturally arrive over the following days as cash flow permits.
# Tried HAND_RAMP_START=2 first ($10,920/$10,081/$9,819, seeds 42/7/99);
# =1 measured slightly better ($11,168/$11,686/$12,446) -- see
# ENABLE_LAND_EXPANSION's comment for the full before/after comparison.
ANIMAL_KEEPER_STAGGER_DAYS = 5  # Phase 14: don't activate the Nth animal-
# keeper role (by animal_order rank -- cow first, then sheep, then goose)
# until N * this many days into the season. A keeper hired before its
# activation day falls back to weed-patrol instead of immediately trying
# to BUY_ANIMAL + build a structure, so cow/sheep/goose purchases ($400 +
# $500 + $300) don't all land in the same early-game cash crunch that
# caused Phase 13's collapse.

# Phase 11 finding: tried a more surgical fix than Phase 10's undifferentiated
# scaling -- one hired hand given a SPECIFIC job (dedicated weed patrol,
# proactive travel + reactive dig) instead of following the same generic
# priority list as the farmer. This directly tests whether targeted
# specialization succeeds where undifferentiated scaling failed.
#
# Weed-patrol hand alone (land still off), vs starter, 3 seeds:
#   seed=42: baseline $26,688  vs  patrol-hand $26,259  (weeds: 9 -> 0)
#   seed=7:  baseline $26,608  vs  patrol-hand $26,513  (weeds: 9 -> 0)
#   seed=99: baseline $26,688  vs  patrol-hand $26,433  (weeds: 9 -> 0)
# The specialization WORKS mechanically -- weeds went to exactly zero in
# all 3 seeds, versus 9 for the baseline. But it's still a small net loss
# (~1-2%, not 13% like Phase 10's undifferentiated version) -- the value
# of the reclaimed tiles doesn't quite cover the hand's overhead. Adding
# land expansion back in on top of the weed-patrol hand made it worse
# again (down to $24,779-25,353), confirming land -- not weeds -- was
# always the harder problem to solve profitably with the labor available.

ANIMAL_BUILD_RESERVE = 1000  # keep this much spare before building a pasture
ENABLE_ANIMALS = True  # Phase 12: enabled -- see finding below
# Phase 12: real leaderboard screenshot (day-30 view of two strong
# players) showed both running cows and sheep at meaningful scale, plus
# multiple hands -- something never tried here. Confirmed the full
# mechanical pipeline empirically (BUY_ANIMAL/BUY_PRODUCT land in the
# shed, not directly in inventory; PICKUP from the shed-adjacent farmer
# spawn tile (4,4) is required before PLACE or FEED will work) before
# writing any code.
#
# Found and fixed a real bug via live tracing: feeding only when
# needs_feed_urgently() fired (which correctly implements the doc's
# "survives first day unfed" grace period) let the keeper wander off on
# weed-patrol fallback duty right when it mattered -- the first cow
# tested escaped from starvation because the fetch-wheat-and-return cycle
# took longer than the grace period allowed. Fixed by feeding on the
# FIRST opportunity each day (not waiting for urgency) and never falling
# back to weed patrol while any animal is unfed.
#
# Result -- THE FIRST configuration in this whole investigation (Phases
# 9-12) to beat the baseline, measured across all 3 established seeds:
#   seed=42: baseline $26,688  vs  +weed-patrol +animal-keeper $28,745  (+7.7%)
#   seed=7:  baseline $26,608  vs  +weed-patrol +animal-keeper $29,255  (+9.9%)
#   seed=99: baseline $26,688  vs  +weed-patrol +animal-keeper $29,673  (+11.2%)
# Enabled by default. One early escape happened in the seed=42 run (day
# 5, before the fix's proactive-feeding logic had fully proven itself in
# practice) but a replacement cow was placed and has stayed healthy
# (fed/cared daily) from day 12 through the end of the season every time
# since -- worth continued monitoring on real leaderboard matches.


def _fib(n):
    """0-indexed Fibonacci matching the doc's cost sequence 1,1,2,3,5,8,13..."""
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _hand_ramp_cap(day):
    """Phase 14: how many hands we're willing to have hired on a given
    day, ramping from HAND_RAMP_START by +1/day up to
    _max_hands_per_day() -- see HAND_RAMP_START's comment for why
    (Phase 13's day-0 cash crash).

    Only ramps when ENABLE_LAND_EXPANSION is on: measured applying the
    ramp with land OFF too, and it was a pure cost (-6.3%, $29,222 vs
    $31,187) -- the proven 6-hand, land-off roster never had a day-0 cash
    crash to fix (it doesn't stack BUY_LAND + 3 simultaneous BUY_ANIMAL on
    top of hiring), so delaying it from 6 immediate hands to a 4-day ramp
    only cost early labor for no offsetting benefit."""
    max_hands = _max_hands_per_day()
    if not ENABLE_LAND_EXPANSION:
        return max_hands
    return min(max_hands, HAND_RAMP_START + day)


def _maybe_hire_hands(me, obs, available_money=None):
    """Return a list of ["HIRE"] orders (0 to the day's ramp cap) queued
    once at the start of each day. Multiple HIRE orders can be queued in
    one turn's market list and process sequentially with increasing
    Fibonacci cost -- confirmed empirically.

    `available_money` (Phase 13) lets decide() pass a running balance that
    already accounts for other spending queued the same turn, instead of
    always checking against the full me["money"] -- see decide()'s
    available_cash comment for why that matters.

    Capped by `_hand_ramp_cap(day)` rather than _max_hands_per_day()
    directly (Phase 14) -- see HAND_RAMP_START's comment for why jumping straight
    to the full roster on day 0 was the real cause of Phase 13's collapse."""
    if not ENABLE_HIRING:
        return []
    if obs["hour"] != 0:
        return []  # only hire at the start of the day
    hires_already = me.get("hires_today", 0)
    if hires_already > 0:
        return []  # already hired this turn/day

    ramp_cap = _hand_ramp_cap(obs.get("day", 0))
    orders = []
    money = me["money"] if available_money is None else available_money
    n = hires_already
    while len(orders) < ramp_cap:
        cost = _fib(n)
        if money - cost < HIRE_CASH_RESERVE:
            break
        orders.append(["HIRE"])
        money -= cost
        n += 1
    return orders


def _next_land_cost(num_unlocked_quadrants):
    """1st extra quadrant costs $1000, 2nd $2000, 3rd $4000 -- confirmed
    empirically for the first two tiers (buying NW->NE cost exactly
    $1000; NE->SW cost exactly $2000); the doc states the third tier
    is $4000."""
    purchases_already_made = num_unlocked_quadrants - 1  # started owning NW
    return 1000 * (2 ** purchases_already_made)


def _maybe_buy_land(me, available_money=None):
    """Return ["BUY_LAND"] if we're running low on space and can afford
    the next quadrant with room to spare, else None.

    `available_money` (Phase 13): see _maybe_hire_hands's docstring --
    same running-balance idea, so a HIRE order queued the same turn
    doesn't get double-counted as still-spendable cash here too."""
    quadrants = me.get("unlocked_quadrants", ["NW"])
    if len(quadrants) >= min(ALL_QUADRANTS, MAX_QUADRANTS_TO_BUY):
        return None
    empty_tiles = tiles_of_kind(me, "EMPTY")
    if len(empty_tiles) >= LAND_BUY_EMPTY_TILE_THRESHOLD:
        return None
    cost = _next_land_cost(len(quadrants))
    money = me["money"] if available_money is None else available_money
    if money >= cost + LAND_BUY_CASH_RESERVE:
        return ["BUY_LAND"]
    return None


def _is_harvestable(tile, obs):
    """True if a plant tile would yield something if HARVESTed right now."""
    if not (isinstance(tile, dict) and tile.get("kind") == "PLANT"):
        return False
    info = CROP_TABLE[tile["crop"]]
    age = crop_age(tile, obs)
    if info["yield_type"] == ONE_TIME:
        return age >= info["first_yield_day"] and tile.get("yield_units", 0) > 0
    if info["yield_type"] == ONGOING:
        return is_scheduled_production_day(tile["crop"], age) or tile.get("yield_units", 0) > 0
    return False


def _choose_next_crop(money, seeds):
    """Pick the most profitable crop to seed next. Prefers a crop we
    already hold a seed for, ranked by revenue/tile/day either way."""
    ranking = best_crop_by_revenue_per_tile_day()
    held = [c for c in ranking if seeds.get(c, 0) > 0]
    if held:
        return held[0]
    for crop in ranking:
        if money >= CROP_TABLE[crop]["seed_cost"]:
            return crop
    return None


def _is_weed(tile):
    return isinstance(tile, dict) and tile.get("kind") == "WEED"


SELLABLE_PRODUCTS = set(CROP_TABLE.keys()) | {"EGG", "MILK", "WOOL"}


def _queue_sell_orders(private, obs):
    """Queue SELL orders for shed inventory, capping quantity per resource
    so we don't crash our own price below MIN_SELL_PRICE_FRACTION of base."""
    from strategy.market import MARKET_PARAMS

    orders = []
    shed = private["shed"]
    market_inventory = obs["market"]["inventory"]
    for resource, qty_in_shed in shed.items():
        if qty_in_shed <= 0 or resource not in SELLABLE_PRODUCTS:
            continue

        inv = market_inventory.get(resource, MARKET_PARAMS[resource]["I0"])
        qty_to_sell = min(qty_in_shed, MAX_SELL_PER_ORDER)
        _, per_unit_prices = estimate_sell_proceeds(resource, inv, qty_to_sell)

        min_acceptable = float(MARKET_PARAMS[resource]["base"]) * MIN_SELL_PRICE_FRACTION
        trimmed_qty = 0
        for unit_price in per_unit_prices:
            if unit_price < min_acceptable:
                break
            trimmed_qty += 1

        if trimmed_qty > 0:
            orders.append(["SELL", resource, trimmed_qty])
    return orders


def _decide_animal_keeper_action(unit_index, position, me, obs, claimed,
                                  seed_budget, seeds_wanted, desired_animal,
                                  animals_wanted, wheat_for_feed_wanted):
    """
    Phase 12 introduced a dedicated hand role for animal husbandry, after a
    real leaderboard screenshot (day-30 view of two strong players) showed
    both running cows and sheep at meaningful scale -- something this
    agent had never attempted. Confirmed the full mechanical pipeline
    empirically first: BUY_ANIMAL and BUY_PRODUCT WHEAT land in the SHED
    (not directly in inventory, unlike seeds); a unit must PICKUP from a
    shed-adjacent tile before it can PLACE an animal or FEED one. The
    farmer's spawn tile (4,4) is shed-adjacent -- confirmed empirically.

    Phase 12 started deliberately small: ONE pasture, ONE cow, to test
    whether animal investment pays off at all before scaling up. It did
    (+7.7% to +11.2% vs baseline). Phase 13 generalizes this to one
    dedicated keeper PER animal type (`desired_animal`, one call site per
    entry in ANIMAL_TABLE -- cow, sheep, goose) so the farm diversifies
    instead of stopping at a single cow. Each keeper only ever builds/
    tends its own `desired_animal`'s structure kind (PASTURE for cow/sheep,
    COOP for goose); cow- and sheep-keepers both target PASTURE tiles, so
    `claimed` is used to keep them from both walking toward the same empty
    one. Priority, checked in order:
      1. Maintain an animal we're standing on (any animal, not just our
         own -- feed if carrying wheat, harvest if ready, care if not yet
         cared for today, collect fertilizer if available).
      1b. Any unfed animal anywhere on the farm takes priority over
          everything below -- go fetch wheat and feed it. Never falls
          through to weed patrol while an animal is waiting unfed.
      2. If carrying our `desired_animal`, travel to an unoccupied
         matching structure and PLACE it.
      3. If a matching structure exists but is unoccupied and nothing is
         en route, request one (animals_wanted) and fetch it once bought.
      4. If we don't have a structure holding `desired_animal` yet and can
         afford to build one, BUILD_PASTURE or BUILD_COOP as appropriate.
      5. Otherwise fall back to the weed-patrol role, so this hand isn't
         wasted on days there's nothing animal-related to do.

    `animals_wanted` is a shared set decide() reads after all units are
    processed, to queue one BUY_ANIMAL per animal type actually requested.
    """
    private = obs["private"]
    x, y = position
    tile = me["tiles"][y][x]
    inventory = private["inventories"][unit_index] if unit_index < len(private["inventories"]) else {}
    shed_pos = (4, 4)  # confirmed empirically: farmer's spawn is shed-adjacent
    structure_kind = ANIMAL_TABLE[desired_animal]["structure"]
    build_action = "BUILD_PASTURE" if structure_kind == "PASTURE" else "BUILD_COOP"

    # Priority 1: maintain an animal we're standing on. Feed on the FIRST
    # opportunity each day, not just when needs_feed_urgently() fires --
    # that check has a correct "survives first day unfed" grace period,
    # but waiting for actual urgency before feeding, combined with the
    # keeper wandering off on weed-patrol fallback duty in the meantime,
    # meant it was sometimes too far away to get back before the animal
    # escaped (confirmed via live trace -- feed was skipped as "not
    # urgent" while standing right there with wheat in hand).
    if is_structure_occupied(tile):
        if not tile.get("fed_today", False) and inventory.get("WHEAT", 0) > 0:
            return ["FEED"]
        if is_ready_to_harvest_animal(tile):
            return ["HARVEST"]
        if needs_care(tile):
            return ["CARE"]
        if fertilizer_ready(tile):
            return ["COLLECT_FERTILIZER"]

    # Priority 1b: if any live animal on the farm isn't fed today yet,
    # this is the keeper's job above everything except an emergency --
    # go get wheat if not carrying any, then head straight for the
    # animal. This deliberately does NOT fall through to weed patrol
    # while an unfed animal is waiting, unlike the earlier version that
    # let the keeper wander away right when it mattered most. Checks both
    # structure kinds (Phase 13: the Phase 12 version only checked PASTURE,
    # a latent gap that never mattered while cow was the only animal).
    unfed_animal_tiles = [
        (tx, ty) for (tx, ty) in tiles_of_kind(me, "PASTURE") + tiles_of_kind(me, "COOP")
        if is_structure_occupied(me["tiles"][ty][tx])
        and not me["tiles"][ty][tx].get("fed_today", False)
    ]
    if unfed_animal_tiles:
        if inventory.get("WHEAT", 0) == 0:
            wheat_for_feed_wanted[0] = True
            if position != shed_pos:
                step = direction_toward(me, position, shed_pos)
                if step:
                    return [step]
            elif private["shed"].get("WHEAT", 0) > 0:
                return ["PICKUP", "WHEAT", private["shed"]["WHEAT"]]
        else:
            target = nearest(position, unfed_animal_tiles)
            if target:
                step = direction_toward(me, position, target)
                if step:
                    return [step]

    # Priority 2: carrying our desired animal -> deliver it to an empty
    # matching structure.
    if inventory.get(desired_animal, 0) > 0:
        if is_structure_unoccupied(tile) and tile.get("kind") == structure_kind:
            return ["PLACE", desired_animal]
        empty_structures = [
            (tx, ty) for (tx, ty) in tiles_of_kind(me, structure_kind)
            if is_structure_unoccupied(me["tiles"][ty][tx]) and (tx, ty) not in claimed
        ]
        target = nearest(position, empty_structures)
        if target:
            step = direction_toward(me, position, target)
            if step:
                claimed.add(target)
                return [step]

    # Priority 3: a matching structure exists unoccupied -- go fetch our animal.
    unoccupied = [
        (tx, ty) for (tx, ty) in tiles_of_kind(me, structure_kind)
        if is_structure_unoccupied(me["tiles"][ty][tx]) and (tx, ty) not in claimed
    ]
    if unoccupied:
        animals_wanted.add(desired_animal)
        if inventory.get("WHEAT", 0) == 0 and position != shed_pos:
            step = direction_toward(me, position, shed_pos)
            if step:
                return [step]
        elif position == shed_pos:
            if private["shed"].get(desired_animal, 0) > 0:
                return ["PICKUP", desired_animal, 1]

    # Priority 4: we don't have our own animal placed yet -- build a
    # structure for it if affordable and none is already unoccupied/en route.
    already_have_mine = any(
        me["tiles"][ty][tx].get("animal") == desired_animal
        for (tx, ty) in tiles_of_kind(me, structure_kind)
    )
    if not unoccupied and not already_have_mine and inventory.get(desired_animal, 0) == 0:
        if me["money"] >= ANIMAL_BUILD_RESERVE:
            if tile is None:
                return [build_action]
            empty_tiles = [t for t in tiles_of_kind(me, "EMPTY") if t not in claimed]
            target = nearest(position, empty_tiles)
            if target:
                step = direction_toward(me, position, target)
                if step:
                    claimed.add(target)
                    return [step]

    # Priority 5: fall back to weed patrol so this hand isn't idle.
    return _decide_weed_patrol_action(position, me, obs, claimed, seed_budget, seeds_wanted)


def _decide_weed_patrol_action(position, me, obs, claimed, seed_budget, seeds_wanted):
    """
    Phase 11: a dedicated role for one hired hand, tried after undifferentiated
    multi-unit scaling (Phase 10) measured a consistent ~13% loss across 3
    seeds despite mechanically correct HIRE/BUY_LAND. The hypothesis: extra
    labor pays off when given a specific job the farmer can't profitably do
    alone (proactive weed-clearing measured as a net negative for a SOLE
    farmer in Phase 7, precisely because it traded off against that farmer's
    more valuable planting/harvesting time -- a dedicated hand has no such
    tradeoff if there's nothing else pulling on it).

    Priority: protect/harvest first (never let a real emergency go unhandled
    even on patrol), THEN weed-clearing (proactive travel, not just
    reactive), and only fall back to general planting duty if the farm is
    currently weed-free.
    """
    x, y = position
    tile = me["tiles"][y][x]

    if needs_water_urgently(tile):
        return ["WATER"]
    if _is_harvestable(tile, obs):
        return ["HARVEST"]
    if _is_weed(tile):
        return ["DIG"]

    weed_tiles = [t for t in tiles_of_kind(me, "WEED") if t not in claimed]
    target = nearest(position, weed_tiles)
    if target:
        step = direction_toward(me, position, target)
        if step:
            claimed.add(target)
            return [step]

    # No weeds anywhere right now -- fall back to general duty so this
    # hand isn't wasted while the farm happens to be clean.
    return _decide_unit_action(position, me, obs, claimed, seed_budget, seeds_wanted)


def _decide_unit_action(position, me, obs, claimed, seed_budget, seeds_wanted, zone=None):
    """
    Decide a single action for one unit (farmer or hand) standing at
    `position`, using the same priority order as the original single-unit
    planner. `claimed` is a shared set of (x,y) travel targets already
    taken by earlier units this turn -- excluded from this unit's target
    search so two units don't walk toward the same tile. `seed_budget` is
    a shared {crop: count} dict simulating currently-held seeds, mutated
    in place as units are assigned to PLANT (see module docstring for why
    this matters). `seeds_wanted` is a shared {crop: count} dict this
    function increments when a unit wants to plant a crop it doesn't
    currently have budget for, so decide() can queue a BUY_SEED with the
    right quantity for next turn -- with multiple units active, a single
    unit's worth of seed is not enough (this under-bought seed for the
    other units when this was a plain set instead of a counted dict).

    `zone` (Phase 13: one of "NW"/"NE"/"SW"/"SE", or None) restricts this
    unit's travel-target search to that quadrant -- see decide()'s
    zone-farmer dispatch. A quadrant's locked tiles are the string
    "LOCKED", never None/PLANT/WEED, so they were already invisible to
    tiles_of_kind() before this; `zone` additionally keeps units that
    share an UNLOCKED board from clustering on whichever region has the
    closest work, so a newly bought quadrant reliably gets its own
    dedicated worker instead of competing for farm-wide attention. The
    tile the unit is currently standing on (priorities 1/2/7 below) is
    always acted on regardless of zone -- there's no reason to ignore an
    emergency directly underfoot.

    Returns the action list, e.g. ["WATER"], ["PLANT", "MELON"], ["NORTH"].
    """
    private = obs["private"]
    x, y = position
    tile = me["tiles"][y][x]
    board_size = len(me["tiles"])

    def _in_zone(xy):
        return zone is None or quadrant_of(xy[0], xy[1], board_size) == zone

    # Priority 1: protect assets.
    if needs_water_urgently(tile):
        return ["WATER"]

    # Priority 2: harvest.
    if _is_harvestable(tile, obs):
        return ["HARVEST"]

    # Priority 3: travel toward nearest urgently-thirsty plant.
    thirsty_tiles = [
        (tx, ty) for (tx, ty) in tiles_of_kind(me, "PLANT")
        if needs_water_urgently(me["tiles"][ty][tx]) and (tx, ty) not in claimed and _in_zone((tx, ty))
    ]
    target = nearest(position, thirsty_tiles)
    if target:
        step = direction_toward(me, position, target)
        if step:
            claimed.add(target)
            return [step]

    # Priority 4: travel toward nearest harvestable plant.
    harvestable_tiles = [
        (tx, ty) for (tx, ty) in tiles_of_kind(me, "PLANT")
        if _is_harvestable(me["tiles"][ty][tx], obs) and (tx, ty) not in claimed and _in_zone((tx, ty))
    ]
    target = nearest(position, harvestable_tiles)
    if target:
        step = direction_toward(me, position, target)
        if step:
            claimed.add(target)
            return [step]

    # Priority 5/6: plant, respecting the shared seed budget. Even without
    # seed in hand yet (a BUY_SEED queued this turn won't land until next
    # turn), it's still worth positioning toward an empty tile so we're
    # ready to plant the moment the seed arrives, rather than defaulting
    # to weed-digging while there's real expansion work to do.
    next_crop = _choose_next_crop(me["money"], private["seeds"])
    if next_crop:
        available = seed_budget.get(next_crop, 0)
        if available <= 0:
            seeds_wanted[next_crop] = seeds_wanted.get(next_crop, 0) + 1
        if tile is None and available > 0:
            seed_budget[next_crop] = available - 1
            return ["PLANT", next_crop]
        if tile is not None or available <= 0:
            empty_tiles = [
                t for t in tiles_of_kind(me, "EMPTY") if t not in claimed and _in_zone(t)
            ]
            target = nearest(position, empty_tiles)
            if target:
                step = direction_toward(me, position, target)
                if step:
                    claimed.add(target)
                    return [step]

    # Priority 7: reactive weed digging (see module docstring).
    if _is_weed(tile):
        return ["DIG"]

    return ["PASS"]


def decide(obs):
    me = my_farm(obs)
    private = obs["private"]

    claimed = set()
    seed_budget = dict(private["seeds"])  # simulated, decremented as units plant
    seeds_wanted = {}  # {crop: count} -- how many more units want to plant it
    animals_wanted = set()  # {"COW", "SHEEP", ...} -- which types to BUY_ANIMAL for
    wheat_for_feed_wanted = [False]

    # Phase 13: the farmer is zone-restricted to NW, its home quadrant
    # (spawns there every day -- confirmed in the engine's _default_spawn).
    # This is a no-op before any land is bought (NW is the only unlocked
    # quadrant anyway) and keeps the farmer from wandering off to help a
    # zone-farmer's quadrant once others are unlocked, mirroring the split
    # below.
    farmer_pos = tuple(me["farmer"])
    farmer_action = _decide_unit_action(farmer_pos, me, obs, claimed, seed_budget, seeds_wanted, zone="NW")

    # Phase 13: hand[0] is a dedicated weed-patrol role (Phase 11, farm-
    # wide -- weeds are sparse enough that zoning would just leave some
    # unattended); hands[1 .. len(animal_order)] are dedicated animal-
    # keepers, one per animal type ranked by revenue/tile/day (cow, sheep,
    # goose -- confirmed via best_animal_by_revenue_per_tile_day()), also
    # farm-wide since they need to freely reach the shed and any animal
    # regardless of quadrant. Remaining hands are zone-farmers, one per
    # quadrant in ZONE_ORDER (the engine's actual land-purchase order --
    # confirmed by reading kaggriculture.py's LAND_ORDER) -- each restricted
    # to its own quadrant via _decide_unit_action's `zone` so that a newly
    # bought quadrant gets a dedicated worker instead of competing with
    # everyone else's farm-wide nearest-target search (the Phase 9-11-13
    # land-expansion losses were consistently this coordination problem,
    # not a labor-shortage problem). A zone-farmer whose quadrant isn't
    # unlocked yet falls back to farm-wide duty so it isn't wasted.
    #
    # Phase 14: when ENABLE_LAND_EXPANSION is on, each animal-keeper slot
    # only takes on its role once the season reaches `keeper_slot *
    # ANIMAL_KEEPER_STAGGER_DAYS` -- before that it patrols weeds instead,
    # so cow/sheep/goose purchases land several days apart rather than all
    # competing for cash on day 0 (see ANIMAL_KEEPER_STAGGER_DAYS's comment
    # for why). Skipped when land expansion is off, same reasoning as
    # _hand_ramp_cap: the proven land-off roster activates all 3 keepers
    # immediately and was never the source of the day-0 cash crash.
    animal_order = best_animal_by_revenue_per_tile_day()
    unlocked = me.get("unlocked_quadrants", ["NW"])
    day = obs.get("day", 0)
    hand_actions = []
    for i, hand_pos in enumerate(me.get("hands", [])):
        keeper_slot = i - 1
        zone_slot = i - 1 - len(animal_order)
        pos = tuple(hand_pos)
        if i == 0 and ENABLE_HIRING:
            hand_actions.append(
                _decide_weed_patrol_action(pos, me, obs, claimed, seed_budget, seeds_wanted)
            )
        elif (ENABLE_HIRING and ENABLE_ANIMALS and 0 <= keeper_slot < len(animal_order)
              and ENABLE_LAND_EXPANSION and day < keeper_slot * ANIMAL_KEEPER_STAGGER_DAYS):
            hand_actions.append(
                _decide_weed_patrol_action(pos, me, obs, claimed, seed_budget, seeds_wanted)
            )
        elif ENABLE_HIRING and ENABLE_ANIMALS and 0 <= keeper_slot < len(animal_order):
            hand_actions.append(
                _decide_animal_keeper_action(
                    i + 1, pos, me, obs, claimed, seed_budget, seeds_wanted,
                    animal_order[keeper_slot], animals_wanted, wheat_for_feed_wanted,
                )
            )
        elif ENABLE_HIRING and 0 <= zone_slot < len(ZONE_ORDER) and ZONE_ORDER[zone_slot] in unlocked:
            hand_actions.append(
                _decide_unit_action(pos, me, obs, claimed, seed_budget, seeds_wanted, zone=ZONE_ORDER[zone_slot])
            )
        else:
            hand_actions.append(
                _decide_unit_action(pos, me, obs, claimed, seed_budget, seeds_wanted)
            )

    # Market orders. Phase 13 fix #1: HIRE and BUY_LAND are queued FIRST --
    # they're once-a-day, time-sensitive decisions (a missed HIRE means a
    # hand that never shows up at all today). SELL orders are queued LAST
    # and explicitly trimmed to stay under maxMarketOrdersPerTurn (default
    # 10, per the doc) -- previously sell orders were queued first, so a
    # shed with several sellable resources could silently push HIRE/
    # BUY_LAND past the engine's per-turn cap and lose them with no
    # warning, exactly the kind of failure that's invisible in aggregate
    # money totals but compounds daily.
    #
    # Phase 13 fix #2: every spend category below independently checked
    # its own cost against the full me["money"] -- correct in isolation,
    # but each category was blind to what every OTHER category queued the
    # same turn. With just cow-only animals (Phase 12) this rarely mattered
    # (one modest purchase), but stacking HIRE (up to 9 hands), BUY_LAND
    # (up to $4,000), BUY_SEED, and 3x BUY_ANIMAL in the same turn (Phase
    # 13's zone-farmer trial) let every category pass its own reserve check
    # against the SAME undiminished balance, and the engine then processed
    # them sequentially for real -- crashed money to $9 by day 3 in one
    # trial. `available_cash` is a single running balance, decremented as
    # each category commits spend, so later checks see the truth.
    available_cash = me["money"]
    market = []

    hire_orders = _maybe_hire_hands(me, obs, available_cash) if ENABLE_HIRING else []
    market.extend(hire_orders)
    available_cash -= sum(_fib(i) for i in range(len(hire_orders)))

    if ENABLE_LAND_EXPANSION:
        land_order = _maybe_buy_land(me, available_cash)
        if land_order:
            market.append(land_order)
            quadrants = me.get("unlocked_quadrants", ["NW"])
            available_cash -= _next_land_cost(len(quadrants))

    # Queue BUY_SEED orders for next turn sized to how many units actually
    # wanted to plant each crop this turn, capped by what we can afford --
    # buying only 1 regardless of demand was a real bug (see docstring).
    for crop, wanted_qty in seeds_wanted.items():
        seed_cost = CROP_TABLE[crop]["seed_cost"]
        affordable_qty = max(1, int(available_cash // seed_cost)) if available_cash >= seed_cost else 0
        qty = min(wanted_qty, affordable_qty) if affordable_qty else wanted_qty
        if qty > 0:
            market.append(["BUY_SEED", crop, qty])
            available_cash -= qty * seed_cost

    if ENABLE_ANIMALS:
        for animal_name in animals_wanted:
            cost = ANIMAL_TABLE[animal_name]["animal_cost"]
            if private["shed"].get(animal_name, 0) == 0 and available_cash >= cost:
                market.append(["BUY_ANIMAL", animal_name, 1])
                available_cash -= cost
        wheat_cost = price("WHEAT", obs["market"]["inventory"]["WHEAT"]) * 5
        if wheat_for_feed_wanted[0] and available_cash >= wheat_cost:
            market.append(["BUY_PRODUCT", "WHEAT", 5])
            available_cash -= wheat_cost

    room_left = max(0, MAX_MARKET_ORDERS_PER_TURN - len(market))
    market.extend(_queue_sell_orders(private, obs)[:room_left])

    return {"farmer": farmer_action, "hands": hand_actions, "market": market}
