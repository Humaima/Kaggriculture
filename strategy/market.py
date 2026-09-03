"""
Phase 4: the market price curve, encoded from the competition's Price
Function table and verified against its worked P(I0-T)/P(I0+T)/P(I0+2T)
checkpoints in tests/test_market.py.

    price(inv) = base + sign * amp * f(|inv - I0|)
      sign = +1 if inv < I0 (scarcity -> price up)
      sign = -1 if inv > I0 (glut -> price down)
      amp  = target * base / f(T)   (derived, not stored)
      f in {linear, sq, sqrt, log, log10}, log(x) = ln(1+x)
    Floored at $1, rounded to the nearest dollar.
"""

import math
from typing import cast

# ---- shape functions -------------------------------------------------

def _linear(x):
    return x


def _sq(x):
    return x ** 2


def _sqrt(x):
    return math.sqrt(x)


def _log(x):
    return math.log(1 + x)  # ln(1+x) so f(0) == 0


def _log10(x):
    return math.log10(1 + x)


SHAPE_FUNCS = {
    "linear": _linear,
    "sq": _sq,
    "sqrt": _sqrt,
    "log": _log,
    "log10": _log10,
}

# ---- per-resource parameters (from the Price Function table) ---------
# Each entry: base, I0, T, below_func, below_target, above_func, above_target

MARKET_PARAMS = {
    "WHEAT":      dict(base=25,  I0=10_000, T=400, below_func="sqrt",   below_target=0.80,
                        above_func="log",    above_target=0.20),
    "CARROT":     dict(base=35,  I0=10_000, T=450, below_func="log",    below_target=0.20,
                        above_func="sqrt",   above_target=0.70),
    "TOMATO":     dict(base=60,  I0=10_000, T=200, below_func="linear", below_target=0.40,
                        above_func="sqrt",   above_target=0.60),
    "STRAWBERRY": dict(base=120, I0=10_000, T=100, below_func="sqrt",   below_target=0.70,
                        above_func="linear", above_target=1.60),
    "MELON":      dict(base=250, I0=10_000, T=300, below_func="log",    below_target=0.20,
                        above_func="sq",     above_target=3.60),
    "EGG":        dict(base=50,  I0=10_000, T=332, below_func="linear", below_target=0.40,
                        above_func="log",    above_target=0.20),
    "MILK":       dict(base=160, I0=10_000, T=122, below_func="sqrt",   below_target=0.60,
                        above_func="linear", above_target=1.60),
    "WOOL":       dict(base=200, I0=10_000, T=105, below_func="log",    below_target=0.20,
                        above_func="sq",     above_target=3.20),
    "FERTILIZER": dict(base=100, I0=10_000, T=200, below_func="linear", below_target=0.40,
                        above_func="linear", above_target=0.40),
}


def price(resource, inventory):
    """Compute the current sell price for `resource` at a given market
    inventory level, matching the engine's formula exactly."""
    p = MARKET_PARAMS[resource]
    diff = inventory - p["I0"]
    if diff == 0:
        return p["base"]

    if diff < 0:
        f = SHAPE_FUNCS[cast(str, p["below_func"])]
        target = p["below_target"]
        sign = 1
    else:
        f = SHAPE_FUNCS[cast(str, p["above_func"])]
        target = p["above_target"]
        sign = -1

    amp = cast(float, target) * cast(int, p["base"]) / f(cast(int, p["T"]))
    computed = p["base"] + sign * amp * f(abs(diff))
    return max(1, round(computed))


def estimate_sell_proceeds(resource, current_inventory, quantity):
    """
    Walk a SELL order unit-by-unit the way the engine processes it, to
    estimate total proceeds and the price impact of a batch sell. This is
    a planning tool for "don't crash your own price" decisions -- it's an
    approximation when other players are also trading concurrently, but
    it's exact for a single player's own order in isolation.
    """
    total = 0
    inv = current_inventory
    per_unit_prices = []
    for _ in range(quantity):
        unit_price = int(price(resource, inv))
        total += unit_price
        per_unit_prices.append(unit_price)
        if unit_price > 1:  # floored sells don't add inventory (per spec)
            inv += 1
    return total, per_unit_prices


def estimate_buy_cost(resource, current_inventory, quantity):
    """Same idea in reverse for BUY_PRODUCT orders (WHEAT, FERTILIZER only).
    The buy price is quoted at post-buy inventory per the spec."""
    total = 0
    inv = current_inventory
    per_unit_prices = []
    for _ in range(quantity):
        inv += 1
        unit_price = int(price(resource, inv))
        total += unit_price
        per_unit_prices.append(unit_price)
    return total, per_unit_prices
