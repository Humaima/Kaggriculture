"""
Phase 4: crop economics, encoded from the competition's Object Types
table and the Harvest Yields rules.

Important: the engine already tracks the authoritative yield_units,
planted_day, and max_lifespan_step directly on each tile (see obs -- a
real PLANT tile looks like {'kind': 'PLANT', 'crop': 'WHEAT',
'planted_day': 0, 'watered_today': True, 'consecutive_unwatered': 1,
'yield_units': 1, 'max_lifespan_step': 120, 'fertilized_until_day': -1},
confirmed via tools/inspect_obs.py). This module does NOT try to
recompute what the engine already tells you -- it exists for planning
decisions the engine doesn't hand you directly: which crop is most
profitable to plant next, and whether a tile is currently inside its
fertilizer-bonus window.
"""

ONE_TIME = "one_time"
ONGOING = "ongoing"

CROP_TABLE = {
    "WHEAT": dict(
        yield_type=ONE_TIME, seed_cost=10, base_price=25,
        first_yield_day=2, max_yield_day=4,
        max_yield=6, max_yield_unfertilized=4,
        bonus_window=(2, 4),  # ceil(4/2)=2 .. max_yield_day=4
        yield_per_tile_day=0.80,
    ),
    "CARROT": dict(
        yield_type=ONE_TIME, seed_cost=20, base_price=35,
        first_yield_day=2, max_yield_day=3,
        max_yield=4, max_yield_unfertilized=3,
        bonus_window=(2, 3),  # ceil(3/2)=2 .. max_yield_day=3
        yield_per_tile_day=0.75,
    ),
    "MELON": dict(
        yield_type=ONE_TIME, seed_cost=80, base_price=250,
        first_yield_day=10, max_yield_day=10,
        max_yield=6, max_yield_unfertilized=6,
        # Doc explicitly documents this as an exception to the general
        # ceil(max_yield_day/2) rule: window is ages 6-12, watering caps
        # at 6 by age 10, fertilizing caps at 6 by age 8.
        bonus_window=(6, 12),
        cap_age_watered=10, cap_age_fertilized=8,
        yield_per_tile_day=0.55,
    ),
    "TOMATO": dict(
        yield_type=ONGOING, seed_cost=50, base_price=60,
        first_yield_day=8, max_yield_day=11,
        max_yield=4, schedule_ages=(8, 9, 10, 11),
        yield_per_tile_day=0.33,
    ),
    "STRAWBERRY": dict(
        yield_type=ONGOING, seed_cost=100, base_price=120,
        first_yield_day=10, max_yield_day=16,
        max_yield=4, schedule_ages=(10, 12, 14, 16),
        yield_per_tile_day=0.24,
    ),
}


def is_in_bonus_window(crop, age):
    """True if a one-time crop at this age is still inside its
    fertilizer/water bonus window (worth fertilizing/watering for extra
    yield, as opposed to just maintaining it to avoid weed decay)."""
    info = CROP_TABLE[crop]
    if info["yield_type"] != ONE_TIME:
        return False
    start, end = info["bonus_window"]
    return start <= age <= end


def is_scheduled_production_day(crop, age):
    """For ongoing crops (tomato, strawberry): True if this age is one of
    the fixed production ages, i.e. a day HARVEST will actually yield
    something rather than being a no-op."""
    info = CROP_TABLE[crop]
    if info["yield_type"] != ONGOING:
        return False
    return age in info["schedule_ages"]


def revenue_per_tile_day_estimate(crop):
    """
    Rough profitability estimate for comparing crops when choosing what
    to plant next: yield_per_tile_day * base_price. This ignores market
    price movement from your own selling -- use market.estimate_sell_proceeds
    for a sharper estimate once you know how much you'll actually sell at
    once.
    """
    info = CROP_TABLE[crop]
    return info["yield_per_tile_day"] * info["base_price"]


def best_crop_by_revenue_per_tile_day():
    """Rank crops by the rough revenue_per_tile_day_estimate, highest first."""
    return sorted(
        CROP_TABLE.keys(),
        key=revenue_per_tile_day_estimate,
        reverse=True,
    )
