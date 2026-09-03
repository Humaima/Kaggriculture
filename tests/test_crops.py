"""
Unit tests for strategy/crops.py, checked against the specific worked
facts published in the competition doc (melon's bonus-window exception,
wheat/carrot's unfertilized caps).

Run from the project root:
    .venv/bin/python tests/test_crops.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy.crops import (
    CROP_TABLE,
    is_in_bonus_window,
    is_scheduled_production_day,
    revenue_per_tile_day_estimate,
    best_crop_by_revenue_per_tile_day,
)


def test_wheat_bonus_window_matches_doc():
    # Doc: watering alone peaks wheat at 4 (base 1 + 3 bonus days)
    assert is_in_bonus_window("WHEAT", 1) is False
    assert is_in_bonus_window("WHEAT", 2) is True
    assert is_in_bonus_window("WHEAT", 4) is True
    assert is_in_bonus_window("WHEAT", 5) is False
    bonus_days = sum(1 for age in range(0, 6) if is_in_bonus_window("WHEAT", age))
    assert bonus_days == 3
    assert 1 + bonus_days == CROP_TABLE["WHEAT"]["max_yield_unfertilized"]


def test_carrot_bonus_window_matches_doc():
    assert is_in_bonus_window("CARROT", 2) is True
    assert is_in_bonus_window("CARROT", 3) is True
    assert is_in_bonus_window("CARROT", 4) is False
    bonus_days = sum(1 for age in range(0, 5) if is_in_bonus_window("CARROT", age))
    assert 1 + bonus_days == CROP_TABLE["CARROT"]["max_yield_unfertilized"]


def test_melon_bonus_window_is_the_documented_exception():
    # Doc: window is ages 6-12 (not the general ceil(10/2)=5 rule),
    # watering reaches the cap of 6 at age 10, ages 11-12 add nothing.
    assert is_in_bonus_window("MELON", 5) is False
    assert is_in_bonus_window("MELON", 6) is True
    assert is_in_bonus_window("MELON", 12) is True
    assert is_in_bonus_window("MELON", 13) is False
    watered_days_to_cap = sum(
        1 for age in range(6, 11) if is_in_bonus_window("MELON", age)
    )
    assert 1 + watered_days_to_cap == CROP_TABLE["MELON"]["max_yield"]  # == 6


def test_tomato_scheduled_production_ages():
    for age in (8, 9, 10, 11):
        assert is_scheduled_production_day("TOMATO", age) is True
    assert is_scheduled_production_day("TOMATO", 7) is False
    assert is_scheduled_production_day("TOMATO", 12) is False


def test_strawberry_scheduled_production_ages_are_every_other_day():
    for age in (10, 12, 14, 16):
        assert is_scheduled_production_day("STRAWBERRY", age) is True
    assert is_scheduled_production_day("STRAWBERRY", 11) is False


def test_one_time_crops_never_have_scheduled_production_days():
    assert is_scheduled_production_day("WHEAT", 2) is False


def test_revenue_ranking_puts_melon_or_strawberry_near_the_top():
    ranking = best_crop_by_revenue_per_tile_day()
    # Sanity: wheat (cheap staple) should not out-rank melon (high value)
    # on this rough per-tile-day estimate.
    assert ranking.index("MELON") < ranking.index("WHEAT")


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
    print(f"\n{passed} passed, {failed} failed")
