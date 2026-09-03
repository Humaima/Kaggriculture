"""
Phase 2 helpers: turn the raw obs dict (as documented in the competition
page, and confirmed live via tools/inspect_obs.py) into small, testable
functions. Keep all "reach into obs[...]" indexing here so the planner
never touches raw obs directly.
"""

from collections import deque

BOARD_SIZE = 10  # default boardSize; tiles is boardSize x boardSize


def my_farm(obs):
    """Return this player's public farm dict."""
    return obs["farms"][obs["player"]]


def opp_farm(obs):
    """Return the opponent's public farm dict (no private shed/seeds visible)."""
    opponent_id = 1 - obs["player"]
    return obs["farms"][opponent_id]


def quadrant_of(x, y, board_size):
    """
    Which quadrant (x, y) belongs to -- NW/NE/SW/SE. Matches the engine's
    own convention exactly (kaggle_environments' kaggriculture.py:
    `half = board_size // 2; ("N" if y < half else "S") + ("W" if x < half else "E")`),
    confirmed by reading the installed package source rather than assumed.
    """
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def tile_at(farm, x, y):
    """Safe tile lookup -- returns None for out-of-bounds instead of raising."""
    if not (0 <= y < len(farm["tiles"]) and 0 <= x < len(farm["tiles"][y])):
        return None
    return farm["tiles"][y][x]


def tiles_of_kind(farm, kind):
    """
    Return a list of (x, y) coordinates matching `kind`, one of:
      "EMPTY"  -> tile is None (unlocked and free)
      "LOCKED" -> tile is the string "LOCKED"
      "PLANT"  -> tile is a plant dict
      "WEED"   -> tile is a weed dict
      "COOP"   -> tile is a structure dict with kind == "COOP"
      "PASTURE"-> tile is a structure dict with kind == "PASTURE"
    """
    matches = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if kind == "EMPTY" and tile is None:
                matches.append((x, y))
            elif kind == "LOCKED" and tile == "LOCKED":
                matches.append((x, y))
            elif isinstance(tile, dict) and tile.get("kind") == kind:
                matches.append((x, y))
    return matches


def crop_age(tile, obs):
    """Age in days of a plant tile. Caller must confirm tile is a PLANT dict."""
    return obs["day"] - tile["planted_day"]


def needs_water_urgently(tile):
    """
    True if a plant tile is one missed watering away from becoming a weed.
    consecutive_unwatered starts at 1 on the planting day itself (no grace
    period) and turns to a weed once it reaches 2 at end-of-day refresh.
    """
    return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get(
        "watered_today", False
    ) and tile.get("consecutive_unwatered", 0) >= 1


def needs_feed_urgently(structure):
    """Same idea as needs_water_urgently, for animal structures."""
    return (
        isinstance(structure, dict)
        and structure.get("kind") in ("COOP", "PASTURE")
        and structure.get("animal") is not None
        and not structure.get("fed_today", False)
        and structure.get("consecutive_unfed", 0) >= 1
    )


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def nearest(from_xy, targets):
    """
    Return the closest (x, y) in `targets` to `from_xy` by Manhattan
    distance. Good enough for an open board -- locked tiles are passable,
    so straight-line distance is a valid approximation of travel cost.
    """
    if not targets:
        return None
    return min(targets, key=lambda t: manhattan(from_xy, t))


def direction_toward(farm, start, goal):
    """
    Return a single movement command ("NORTH"/"SOUTH"/"EAST"/"WEST") that
    takes one step along the shortest path from start to goal, or None if
    start == goal (already there) or goal is unreachable. The game only
    allows one cell of movement per turn, so the planner calls this every
    turn it needs to travel rather than trying to queue multiple moves.
    """
    if start == goal:
        return None
    path = bfs_path(farm, start, goal)
    if not path:
        return None
    next_x, next_y = path[0]
    sx, sy = start
    dx, dy = next_x - sx, next_y - sy
    if dy == -1:
        return "NORTH"
    if dy == 1:
        return "SOUTH"
    if dx == -1:
        return "WEST"
    if dx == 1:
        return "EAST"
    return None  # shouldn't happen on a valid adjacent step


def bfs_path(farm, start, goal):
    """
    Shortest path (list of (x, y) steps, excluding start) from start to
    goal on the farm grid. Locked tiles are passable for movement (only
    tile actions no-op on them), so every in-bounds cell is walkable.
    """
    if start == goal:
        return []
    size = len(farm["tiles"])
    visited = {start}
    queue = deque([(start, [])])
    while queue:
        (x, y), path = queue.popleft()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):  # N, S, W, E
            nx, ny = x + dx, y + dy
            if not (0 <= nx < size and 0 <= ny < size):
                continue
            if (nx, ny) in visited:
                continue
            new_path = path + [(nx, ny)]
            if (nx, ny) == goal:
                return new_path
            visited.add((nx, ny))
            queue.append(((nx, ny), new_path))
    return None  # unreachable (shouldn't happen on an open board)
