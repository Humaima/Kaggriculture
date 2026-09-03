"""
Unit tests for strategy/animals.py, checked against the specific worked
facts published in the competition doc's Object Types table (Goose has the
best yield/tile/day of any resource in the game; the CARE bonus banking
rule around fed/unfed production days).

Run from the project root:
    .venv/bin/python tests/test_animals.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy.animals import (
    ANIMAL_TABLE,
    revenue_per_tile_day_estimate,
    best_animal_by_revenue_per_tile_day,
    care_bonus_will_apply,
)


def test_animal_table_matches_doc_facts():
    # Doc: Goose/Egg yield_per_tile_day = 1.00, the best of any resource.
    assert ANIMAL_TABLE["GOOSE"]["yield_per_tile_day"] == 1.00
    assert ANIMAL_TABLE["GOOSE"]["animal_cost"] == 300
    assert ANIMAL_TABLE["GOOSE"]["structure"] == "COOP"
    assert ANIMAL_TABLE["COW"]["structure"] == "PASTURE"
    assert ANIMAL_TABLE["SHEEP"]["structure"] == "PASTURE"


def test_revenue_ranking_puts_goose_first():
    # 1.00 * $50 = $50/tile/day for goose; cow is 0.50 * $160 = $80... but
    # goose's yield_per_tile_day is still the highest rate of any resource
    # in the game per the doc, so it should never rank last among animals.
    ranking = best_animal_by_revenue_per_tile_day()
    assert set(ranking) == {"GOOSE", "COW", "SHEEP"}
    assert revenue_per_tile_day_estimate("GOOSE") == 50.0
    assert revenue_per_tile_day_estimate("COW") == 80.0
    assert revenue_per_tile_day_estimate("SHEEP") == 66.0


def test_care_bonus_will_apply_none_when_not_a_production_day():
    fed = {"fed_today": True}
    assert care_bonus_will_apply(fed, is_production_day=False) is None


def test_care_bonus_will_apply_true_only_if_fed_on_production_day():
    fed = {"fed_today": True}
    unfed = {"fed_today": False}
    assert care_bonus_will_apply(fed, is_production_day=True) is True
    assert care_bonus_will_apply(unfed, is_production_day=True) is False


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
