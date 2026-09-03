"""
Validates strategy/market.py's price() function against the exact
P(I0-T), P(I0+T), P(I0+2T) checkpoints published in the competition's
Price Function table -- one assertion set per resource. If these ever
fail, the formula or the parameter table has drifted from spec.

Run from the project root:
    .venv/bin/python tests/test_market.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy.market import price, MARKET_PARAMS, estimate_sell_proceeds

# resource -> (P(I0-T), P(I0+T), P(I0+2T)) exactly as published in the doc
EXPECTED = {
    "WHEAT":      (45, 20, 19),
    "CARROT":     (42, 10, 1),
    "TOMATO":     (84, 24, 9),
    "STRAWBERRY": (204, 1, 1),
    "MELON":      (300, 1, 1),
    "EGG":        (70, 40, 39),
    "MILK":       (256, 1, 1),
    "WOOL":       (240, 1, 1),
    "FERTILIZER": (140, 60, 20),
}


def test_price_matches_documented_checkpoints_for_every_resource():
    for resource, (p_minus_t, p_plus_t, p_plus_2t) in EXPECTED.items():
        I0 = int(MARKET_PARAMS[resource]["I0"])
        T = int(MARKET_PARAMS[resource]["T"])
        got_minus = price(resource, I0 - T)
        got_plus = price(resource, I0 + T)
        got_plus2 = price(resource, I0 + 2 * T)
        assert got_minus == p_minus_t, (
            f"{resource} P(I0-T): got {got_minus}, expected {p_minus_t}"
        )
        assert got_plus == p_plus_t, (
            f"{resource} P(I0+T): got {got_plus}, expected {p_plus_t}"
        )
        assert got_plus2 == p_plus_2t, (
            f"{resource} P(I0+2T): got {got_plus2}, expected {p_plus_2t}"
        )


def test_price_at_equilibrium_equals_base():
    for resource, params in MARKET_PARAMS.items():
        assert price(resource, params["I0"]) == params["base"]


def test_price_floor_is_one_dollar():
    # Deep glut should never price below $1
    assert price("MELON", int(MARKET_PARAMS["MELON"]["I0"]) + 100_000) == 1


def test_estimate_sell_proceeds_walks_price_down_unit_by_unit():
    I0 = MARKET_PARAMS["CARROT"]["I0"]
    total, per_unit = estimate_sell_proceeds("CARROT", I0, 5)
    # Selling should push inventory up and price down each step (glut side)
    assert per_unit == sorted(per_unit, reverse=True), (
        f"expected non-increasing prices as we sell into a glut, got {per_unit}"
    )
    assert total == sum(per_unit)


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
