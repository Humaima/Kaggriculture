"""
Phase 4: animal economics, encoded from the competition's Object Types
table and the FEED/CARE/COLLECT_FERTILIZER rules.

Like crops.py, this doesn't recompute what the engine already tracks on
the structure tile (pending_care_bonus, fertilizer_available) -- it
exists for planning: ranking animals by profitability and understanding
the care-bonus banking mechanic well enough to decide when CARE is worth
the action versus other uses of that turn.
"""

ANIMAL_TABLE = {
    "GOOSE": dict(
        structure="COOP", product="EGG", animal_cost=300, build_cost=1,
        base_price=50, first_yield_day=4, interval_days=1,
        max_held=4, yield_per_tile_day=1.00,
    ),
    "COW": dict(
        structure="PASTURE", product="MILK", animal_cost=400, build_cost=1,
        base_price=160, first_yield_day=8, interval_days=2,
        max_held=6, yield_per_tile_day=0.50,
    ),
    "SHEEP": dict(
        structure="PASTURE", product="WOOL", animal_cost=500, build_cost=1,
        base_price=200, first_yield_day=6, interval_days=3,
        max_held=6, yield_per_tile_day=0.33,
    ),
}


def revenue_per_tile_day_estimate(animal):
    """Same rough-profitability idea as crops.revenue_per_tile_day_estimate."""
    info = ANIMAL_TABLE[animal]
    return float(info["yield_per_tile_day"]) * float(info["base_price"])


def best_animal_by_revenue_per_tile_day():
    return sorted(
        ANIMAL_TABLE.keys(),
        key=revenue_per_tile_day_estimate,
        reverse=True,
    )


def care_bonus_will_apply(structure_tile, is_production_day):
    """
    True if CARE-ing this animal today would actually pay off on its next
    scheduled production. Per spec: a banked bonus is only paid out if the
    animal is fed on the production day itself -- an unfed production day
    still yields the base 1 unit but discards the bank. This function
    doesn't predict the future feed state; it's a reminder helper for the
    planner to check "am I about to lose a banked bonus by skipping feed
    today" rather than a full simulation.
    """
    if not is_production_day:
        return None  # not applicable today; CARE still banks for later
    return structure_tile.get("fed_today", False)


def is_structure(tile):
    return isinstance(tile, dict) and tile.get("kind") in ("COOP", "PASTURE")


def is_structure_unoccupied(tile):
    return is_structure(tile) and not tile.get("animal")


def is_structure_occupied(tile):
    return is_structure(tile) and bool(tile.get("animal"))


def is_ready_to_harvest_animal(tile):
    return is_structure_occupied(tile) and tile.get("yield_units", 0) > 0


def needs_care(tile):
    return is_structure_occupied(tile) and not tile.get("cared_today", False)


def fertilizer_ready(tile):
    return is_structure_occupied(tile) and tile.get("fertilizer_available", False)
