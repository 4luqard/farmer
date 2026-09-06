#!/usr/bin/env python3
import math
import random

__all__ = ["laziest_farmer", "_opponent_tracker", "_possible_actions", "_clone_state", "_is_terminal", "_apply_action", "_get_reward"]


# ---- Farmer agent ----

def laziest_farmer(obs):
    """Submitted agent: open with one wheat seed, then do nothing at all.

    Args:
        obs: The observation dict for this step. Only "step" is read.

    Returns:
        An action dict {"farmer", "hands", "market"}: on step 0 the farmer
        PASSes and the market order is one ["BUY_SEED", "WHEAT", 1]; on every
        later step the farmer PASSes and no orders are placed.
    """
    if obs.get("step", 0) == 0:
        return {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}
    return {"farmer": ["PASS"], "hands": [], "market": []}


# ---- Opponent tracking ----

_opponent_cache = {}  # in-memory only: resets on process start, i.e. per match


def _opponent_tracker(obs) -> dict:
    """Summarise the opponent's farm, remembering it for the next step.

    Reads the other player's farm (farms[1 - player]) and stores it in the
    module-global _opponent_cache so the following step can look back at it.
    The cache lives in memory only, so it resets once per match.

    Args:
        obs: The observation dict; "farms", "player" and "step" are read.

    Returns:
        The opponent's farm dict plus two derived keys: "prev_money", their
        money as of the previous step (falling back to their current money at
        step 0, or when the remembered farm carried no money key), and
        "planted_count", the number of PLANT tiles on their grid.
    """
    global _opponent_cache
    current = obs["farms"][1 - obs["player"]]
    previous = {} if obs.get("step") == 0 else _opponent_cache
    _opponent_cache = current
    planted_count = sum(
        1
        for row in current.get("tiles", [])
        for tile in row
        if isinstance(tile, dict) and tile.get("kind") == "PLANT"
    )
    return {
        **current,
        "prev_money": previous.get("money", current.get("money")),
        "planted_count": planted_count,
    }

# ---- Possible actions ----

_SHED_ADJACENT = {(4, 4), (5, 4), (4, 5), (5, 5)}
_BOARD_SIZE = 10
_SHED_CAPACITY = 100
_ANIMALS = {"GOOSE", "COW", "SHEEP"}
_STRUCTURE_ANIMALS = {"COOP": ("GOOSE",), "PASTURE": ("COW", "SHEEP")}
_ANIMAL_PRODUCTS = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}  # python-kit/README.md Object Types table: Goose/Egg, Cow/Milk, Sheep/Wool
_ALL_QUADRANTS = {"NW", "NE", "SW", "SE"}
_SEED_COSTS = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_FIRST_YIELD_DAY = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
_MAX_YIELD_DAY = {"WHEAT": 4, "CARROT": 3, "MELON": 10}  # python-kit/README.md Object Types "Time to Max Yield"; one-time crops only
_ONE_TIME_CROPS = {"WHEAT", "CARROT", "MELON"}  # python-kit/README.md Object Types table
_ANIMAL_COSTS = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_FEED_WHEAT_COST = 1  # WHEAT per FEED; no quantity is documented in python-kit/README.md, inferred from tests/test_apply_action.py:test_feed
_LAND_COSTS = [1000, 2000, 4000]
_QUADRANT_ORDER = ["NW", "NE", "SW", "SE"]  # BUY_LAND unlock order, python-kit/AGENTS.md: "NE, SW, SE ... $1k/$2k/$4k respectively"
_MARKET_I0 = 10000
_PRICE_FLOOR = 1
_MARKET_PARAMS = {  # both sides of the price curve, python-kit/README.md Price Function table L222-232
    "WHEAT":      {"base": 25,  "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base": 35,  "T": 450, "below_func": "log",    "below_target": 0.20, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base": 60,  "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base": 50,  "T": 332, "below_func": "linear", "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}


def _hire_cost(hires_today):
    """Coin cost of the next hire, which grows along the Fibonacci sequence.

    Args:
        hires_today: How many hands have already been hired today.

    Returns:
        The cost of one more hire: 1, 1, 2, 3, 5, ... for 0, 1, 2, 3, 4 hires
        already made today.
    """
    a, b = 1, 1
    for _ in range(hires_today):
        a, b = b, a + b
    return a


def _shape(func, x):
    """Apply a market price curve's shape function.

    Args:
        func: Curve name from _MARKET_PARAMS: "sqrt", "sq", "log", or
            "linear". "log10" is named in python-kit/README.md's abstract
            formula but no resource in the Price Function table actually
            uses it, so it is deliberately omitted.
        x: The curve input; negative values are clamped to 0.

    Returns:
        sqrt(x) for "sqrt", x**2 for "sq", ln(1+x) for "log" (python-kit/
        README.md: "log uses ln(1+x), so f(0)=0"), otherwise x itself —
        unknown names deliberately fall back to the linear curve.
    """
    x = max(0.0, x)
    if func == "sqrt":
        return x ** 0.5
    if func == "sq":
        return x ** 2
    if func == "log":
        return math.log1p(x)
    return x  # "linear" + documented fallback


def _price(item, inv):
    """Market unit price at a given inventory level (python-kit/README.md "The Price Function").

    price(inv) = base + sign * amp * f(|inv - I0|), sign +1 below I0
    (scarcity) and -1 above I0 (glut), amp = target * base / f(T) using
    the matching side's shape function and target, floored at
    _PRICE_FLOOR and rounded to the nearest dollar. At inv == I0 the price
    is exactly base regardless of side.

    Args:
        item: Resource name, a key of _MARKET_PARAMS.
        inv: The market's current inventory of item, at the point (post-buy
            or pre-sell) the caller wants the price quoted.

    Returns:
        The integer unit price.
    """
    p = _MARKET_PARAMS[item]
    base, T = p["base"], p["T"]
    if inv < _MARKET_I0:
        func, target, sign = p["below_func"], p["below_target"], 1
    elif inv > _MARKET_I0:
        func, target, sign = p["above_func"], p["above_target"], -1
    else:
        return base
    amp = target * base / _shape(func, T)
    return max(_PRICE_FLOOR, int(round(base + sign * amp * _shape(func, abs(inv - _MARKET_I0)))))


def _buy_price(item, inv):
    """BUY_PRODUCT unit price: the curve at post-buy inventory (python-kit/README.md L202-214)."""
    return _price(item, inv)


def _land_cost(unlocked):
    """Coin cost of unlocking the next quadrant.

    Args:
        unlocked: The farm's unlocked quadrant names; duplicates are ignored.

    Returns:
        1000, 2000 or 4000 for the 2nd, 3rd or 4th quadrant, or None when no
        quadrant is recorded as unlocked or all four already are.
    """
    n = len(set(unlocked))
    return _LAND_COSTS[n - 1] if 1 <= n <= len(_LAND_COSTS) else None


def _apply_carried_inventory(actions, items):
    """Append the PLACE and DROP actions for one unit's carried items.

    Args:
        actions: The unit's action list, extended in place.
        items: {item: count} the unit is carrying.

    Returns:
        None. actions gains a ["PLACE", item, n] for every partial quantity
        1..count of each item, then a single trailing "DROP" if anything was
        appended.
    """
    dropped = False
    for item, count in items.items():
        for n in range(1, count + 1):
            actions.append(["PLACE", item, n])
            dropped = True
    if dropped:
        actions.append("DROP")


def _shed_pickups(shed):
    """Build the PICKUP actions for a unit standing next to the shed.

    Args:
        shed: {item: count} currently stored in the shed.

    Returns:
        A new list of ["PICKUP", item, n] for every partial quantity 1..count,
        animals first and the shed's own order kept within each group.
    """
    ordered = sorted(shed.items(), key=lambda kv: kv[0] not in _ANIMALS)  # stable: animals first
    return [["PICKUP", item, n] for item, count in ordered for n in range(1, count + 1)]


def _quadrant(pos):
    """Name the quadrant a board position falls in.

    Args:
        pos: (x, y) board position.

    Returns:
        "NW", "NE", "SW" or "SE" — y < 5 is North and x < 5 is West on the
        10x10 board.
    """
    x, y = pos
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _tile_unlocked(farm, pos):
    """Whether a unit's tile sits in a quadrant the farm owns.

    Args:
        farm: The player's farm dict; "unlocked_quadrants" is read.
        pos: (x, y) board position, or None when unknown.

    Returns:
        True when pos falls in an unlocked quadrant. Unknowns are permissive:
        a missing "unlocked_quadrants" key or a None position both count as
        unlocked.
    """
    unlocked = farm.get("unlocked_quadrants")
    if unlocked is None or pos is None:
        return True
    return _quadrant(pos) in unlocked


def _shed_adjacent(pos):
    """Whether a unit can reach the shed from where it stands.

    Args:
        pos: (x, y) board position, or None when unknown.

    Returns:
        True when pos is one of the four centre tiles (4, 4), (5, 4), (4, 5)
        and (5, 5); a None position also counts as adjacent.
    """
    return pos is None or tuple(pos) in _SHED_ADJACENT


def _tile_at(farm, pos):
    """Look up the tile a unit is standing on.

    Args:
        farm: The player's farm dict; "tiles" is a row-major grid indexed
            tiles[y][x].
        pos: (x, y) board position, or None when unknown.

    Returns:
        The tile at pos (a dict, "LOCKED", or None), or None when pos is
        missing, the farm carries no grid, or pos falls off the grid.
    """
    if pos is None:
        return None
    x, y = pos
    tiles = farm.get("tiles")
    if not tiles or y < 0 or y >= len(tiles):
        return None
    row = tiles[y]
    if x < 0 or x >= len(row):
        return None
    return row[x]


def _set_tile(farm, pos, value):
    """Write a new value into the tile a unit stands on.

    Args:
        farm: The player's farm dict, mutated in place; "tiles" is a
            row-major grid indexed tiles[y][x].
        pos: (x, y) board position, or None when unknown.
        value: The new tile to write (a dict, "LOCKED", or None).

    Returns:
        None. No-op when pos is missing, the farm carries no grid, or pos
        falls off the grid (same guards as _tile_at).
    """
    if pos is None:
        return
    x, y = pos
    tiles = farm.get("tiles")
    if not tiles or y < 0 or y >= len(tiles):
        return
    row = tiles[y]
    if x < 0 or x >= len(row):
        return
    row[x] = value


def _new_structure_tile(kind):
    """Build a freshly-placed COOP/PASTURE tile, no animal placed yet.

    Args:
        kind: "COOP" or "PASTURE".

    Returns:
        A tile dict matching python-kit/README.md's animal-structure
        schema, all fields at their just-built defaults. placed_day is
        left at -1 since it dates a placed animal (README.md L115,
        L312-325), not the structure itself; animal is still None here.
    """
    return {
        "kind": kind,
        "animal": None,
        "placed_day": -1,
        "yield_units": 0,
        "fed_today": False,
        "consecutive_unfed": 0,
        "cared_today": False,
        "fertilizer_available": False,
        "pending_care_bonus": 0,
    }


def _movement_actions(pos):
    """List the moves that keep a unit on the board.

    Args:
        pos: (x, y) board position, or None when unknown.

    Returns:
        "PASS" plus the compass directions that stay inside the 10x10 board;
        a None position yields all four directions.
    """
    actions = ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]
    if pos is None:
        return actions
    x, y = pos
    if y == 0:
        actions.remove("NORTH")
    if y == _BOARD_SIZE - 1:
        actions.remove("SOUTH")
    if x == 0:
        actions.remove("WEST")
    if x == _BOARD_SIZE - 1:
        actions.remove("EAST")
    return actions


def _base_actions(unlocked, seed, pos=None, tile=None, carried=None, day=0):
    """List every action one unit can take on the tile it stands on.

    Branches on what the tile holds. A locked tile allows movement only. A
    WEED can be DUG. A PLANT can be WATERed while dry, DUG, FERTILIZEd when
    the unit carries fertilizer and the tile is not already fertilized through
    day, and HARVESTed once it has yield units and has reached its crop's
    first yield day. A COOP or PASTURE can be DUG and have a compatible
    carried animal PLACEd while empty, or be CAREd for, FED wheat, emptied of
    fertilizer and HARVESTed once occupied. Any other tile can be built on or
    planted.

    Args:
        unlocked: Whether the unit's quadrant is owned; falsy means movement
            only.
        seed: {crop: count} of seeds in stock, for the PLANT actions.
        pos: (x, y) board position, or None when unknown.
        tile: The tile the unit stands on, as returned by _tile_at.
        carried: {item: count} the unit is carrying, or None.
        day: The current in-game day, for fertilizer and harvest timing.

    Returns:
        A list mixing bare strings ("DIG") and lists (["PLANT", "WHEAT"],
        ["PLACE", "GOOSE", 1]).
    """
    carried = carried or {}
    actions = _movement_actions(pos)
    if not unlocked:
        return actions
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        actions.append("DIG")
        return actions
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        watered = tile.get("watered_today", False)
        fertilized = tile.get("fertilized_until_day", -1) >= day
        if not watered:
            actions.append("WATER")
        actions.append("DIG")
        if carried.get("FERTILIZER", 0) > 0 and not fertilized:
            actions.append("FERTILIZE")
        age = day - tile.get("planted_day", 0)
        if tile.get("yield_units", 0) > 0 and age >= _FIRST_YIELD_DAY.get(tile.get("crop"), 0):
            actions.append("HARVEST")
        return actions
    if isinstance(tile, dict) and tile.get("kind") in _STRUCTURE_ANIMALS:
        if tile.get("animal") is None:
            actions.append("DIG")
            for animal in _STRUCTURE_ANIMALS[tile["kind"]]:
                if carried.get(animal, 0) > 0:
                    actions.append(["PLACE", animal, 1])
        else:
            if not tile.get("cared_today", False):
                actions.append("CARE")
            if not tile.get("fed_today", False) and carried.get("WHEAT", 0) > 0:
                actions.append("FEED")
            if tile.get("fertilizer_available", False):
                actions.append("COLLECT_FERTILIZER")
            if tile.get("yield_units", 0) > 0:
                actions.append("HARVEST")
        return actions
    actions.extend(["BUILD_COOP", "BUILD_PASTURE"])
    for crop, count in seed.items():
        if count > 0:
            actions.append(["PLANT", crop])
    return actions


def _possible_actions(obs) -> dict:
    """Enumerate every action available to the current player this step.

    Args:
        obs: The observation dict; "farms", "player", "day", the market
            inventory and the "private" seeds, inventories and shed are read.

    Returns:
        {"farmer": [...], "hands": [[...], ...], "market": [...]}, where
        "hands" holds one action list per hired hand. Each unit's list comes
        from _base_actions, plus the shed PICKUP, PLACE and DROP actions when
        that unit stands beside the shed. The market list holds the HIRE,
        BUY_LAND, BUY_SEED, BUY_PRODUCT and BUY_ANIMAL orders the farm can
        afford — dropping the ones that would add to a full shed, and BUY_LAND
        once every quadrant is owned — followed by a ["SELL", item, n] for
        every partial quantity of each non-animal shed item, which needs no
        unit beside the shed.
    """
    seed = obs.get("private", {}).get("seeds", {})

    farms = obs.get("farms", [])
    player = obs.get("player", 0)
    farm = farms[player] if player < len(farms) else {}

    farmer_pos = farm.get("farmer")
    hand_positions = farm.get("hands", [])
    carried = obs.get("private", {}).get("inventories", [])
    shed = obs.get("private", {}).get("shed", {})
    day = obs.get("day", 0)

    farmer = _base_actions(_tile_unlocked(farm, farmer_pos), seed, farmer_pos,
                            _tile_at(farm, farmer_pos), carried[0] if carried else None, day)

    money = farm.get("money")
    inventory = obs.get("market", {}).get("inventory", {})
    unlocked = farm.get("unlocked_quadrants") or ()
    shed_full = sum(shed.values()) >= _SHED_CAPACITY
    market = []
    if money is None or money > 0:
        priced = [
            ("HIRE", _hire_cost(farm.get("hires_today", 0))),
            ("BUY_LAND", _land_cost(unlocked)),
        ]
        priced += [(["BUY_SEED", c, 1], cost) for c, cost in _SEED_COSTS.items()]
        if not shed_full:
            priced += [
                (["BUY_PRODUCT", p, 1], _buy_price(p, inventory.get(p, _MARKET_I0) - 1))
                for p in ("WHEAT", "FERTILIZER")
            ]
            priced += [(["BUY_ANIMAL", a, 1], cost) for a, cost in _ANIMAL_COSTS.items()]
        market = [
            action for action, cost in priced
            if money is None or (cost is not None and cost <= money)
        ]
        if set(unlocked) >= _ALL_QUADRANTS and "BUY_LAND" in market:
            market.remove("BUY_LAND")
    for item, count in shed.items():
        if item not in _ANIMALS:
            for n in range(1, count + 1):
                market.append(["SELL", item, n])

    if _shed_adjacent(farmer_pos):
        farmer.extend(_shed_pickups(shed))
        if not shed_full and carried:
            _apply_carried_inventory(farmer, carried[0])

    hand_lists = []
    for i, hand_pos in enumerate(hand_positions):
        hand_pos = hand_pos or None
        hand_carried = carried[i + 1] if len(carried) > i + 1 else None
        hand = _base_actions(_tile_unlocked(farm, hand_pos), seed, hand_pos,
                             _tile_at(farm, hand_pos), hand_carried, day)
        if _shed_adjacent(hand_pos):
            hand.extend(_shed_pickups(shed))
            if not shed_full and len(carried) > i + 1:
                _apply_carried_inventory(hand, carried[i + 1])
        hand_lists.append(hand)

    return {"farmer": farmer, "hands": hand_lists, "market": market}


# ---- Forward simulation ----

_TURNS_PER_DAY = 24  # python-kit/README.md L355
_EPISODE_STEPS = 720  # python-kit/README.md L351
_MAX_MARKET_ORDERS_PER_TURN = 10  # python-kit/README.md L354
_WEED_SPAWN_CHANCE = 0.005  # python-kit/README.md L357
_TOWN_CENTER_SELL_INTERVAL = 24  # python-kit/README.md L360
_TOWN_SHOP_SELL_INTERVAL = 4  # python-kit/README.md L359
_SHOP_DEMAND = {  # python-kit/README.md Town Buildings table L175-184; only "BAKERY" has a confirmed observation spelling
    "BAKERY":         {"EGG": 1, "WHEAT": 1},
    "PIZZA_SHOP":     {"MILK": 1, "TOMATO": 1, "WHEAT": 1},
    "BRUNCH_SPOT":    {"EGG": 1, "WHEAT": 1, "STRAWBERRY": 1},
    "YARN_STORE":     {"WOOL": 2},
    "ICE_CREAM_SHOP": {"STRAWBERRY": 1, "MILK": 1, "WHEAT": 1},
    "PET_CAFE":       {"CARROT": 2},
    "SMOOTHIE_SHOP":  {"STRAWBERRY": 1, "MILK": 1},
    "FARMERS_MARKET": {"WHEAT": 1, "CARROT": 1, "TOMATO": 1, "STRAWBERRY": 1},
}


def _clone_state(obs, memo=None):
    """Deep-copy an observation so a forward simulation can mutate it freely.

    Args:
        obs: A value from the observation tree — a dict, a list, or a leaf
            (int, str, bool, None, ...).
        memo: {id(source): clone} of objects already copied in this call,
            threaded through the recursion. Callers omit it; the outermost
            call starts a fresh one, mirroring copy.deepcopy.

    Returns:
        A recursive copy: every dict and list is rebuilt fresh, but a source
        object visited more than once (e.g. two grid rows aliasing the same
        list) resolves to the same clone every time instead of diverging
        copies; immutable leaves are returned as-is (they can't be mutated,
        so sharing them is safe and avoids needless copying).
    """
    if memo is None:
        memo = {}
    key = id(obs)
    if key in memo:
        return memo[key]
    if isinstance(obs, dict):
        clone = {}
        memo[key] = clone
        for k, v in obs.items():
            clone[k] = _clone_state(v, memo)
        return clone
    if isinstance(obs, list):
        clone = []
        memo[key] = clone
        for v in obs:
            clone.append(_clone_state(v, memo))
        return clone
    return obs


def _is_terminal(obs):
    """Check whether the season has reached its final turn.

    Args:
        obs: The observation dict for the current turn; reads "day" and
            "hour" (both 0-indexed), defaulting missing values to 0.

    Returns:
        True once elapsed turns (day * turns-per-day + hour) reach the
        season's total turn count; False otherwise.
    """
    return obs.get("day", 0) * _TURNS_PER_DAY + obs.get("hour", 0) >= _EPISODE_STEPS


def _move(pos, action):
    """Apply one movement action to a board position.

    Args:
        pos: [x, y] board position.
        action: "NORTH", "SOUTH", "EAST", "WEST", or any other action (e.g.
            "PASS"), which leaves the position unchanged.

    Returns:
        A new [x, y], one cell closer in that direction; moves off the edge
        of the board are no-ops (python-kit/README.md L43).
    """
    x, y = pos
    if action == "NORTH" and y > 0:
        y -= 1
    elif action == "SOUTH" and y < _BOARD_SIZE - 1:
        y += 1
    elif action == "WEST" and x > 0:
        x -= 1
    elif action == "EAST" and x < _BOARD_SIZE - 1:
        x += 1
    return [x, y]


def _apply_plant(farm, private, pos, crop, day):
    """Plant a seed on the tile a unit stands on, if the tile is empty.

    Args:
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place; "seeds" is
            decremented.
        pos: [x, y] board position of the acting unit, or None.
        crop: The crop to plant, a key of private["seeds"].
        day: The current in-game day, recorded as planted_day.

    Returns:
        None. No-op unless the tile is None (also correctly excludes
        "LOCKED", which _tile_at never returns as None). Otherwise writes a
        fresh PLANT tile: watered_today=False, consecutive_unwatered=1 (a
        new seed's planting day itself counts as its first unwatered day,
        python-kit/README.md "Watering / Animal Feed"), yield_units=0,
        fertilized_until_day=-1, and max_lifespan_left set to
        _MAX_YIELD_DAY[crop] + 1 for one-time crops (README: one-time crops
        "reach max lifespan one day after max_yield_day") or -1 for ongoing
        crops (TOMATO/STRAWBERRY, per the Observation Format schema).
        Decrements private["seeds"][crop] by 1. The all-or-nothing rule for
        multiple simultaneous PLANTs of the same crop ("if you try to plant
        too many in a specific turn, none are planted", README "Plants") is
        the caller's responsibility — _apply_action only calls this for
        crops the pre-pass has determined are affordable this turn.
    """
    if _tile_at(farm, pos) is not None:
        return
    max_lifespan_left = _MAX_YIELD_DAY[crop] + 1 if crop in _ONE_TIME_CROPS else -1
    _set_tile(farm, pos, {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": day,
        "watered_today": False,
        "consecutive_unwatered": 1,
        "yield_units": 0,
        "max_lifespan_left": max_lifespan_left,
        "fertilized_until_day": -1,
    })
    seeds = private.setdefault("seeds", {})
    seeds[crop] = seeds.get(crop, 0) - 1


def _apply_place(farm, private, index, pos, item, n):
    """Apply one unit's PLACE action, if it has an effect.

    python-kit/README.md, "Animals": PLACE has two mutually exclusive
    variants, chosen by what the unit stands on — this needs both farm (to
    check the tile) and private (to mutate inventory) together, which
    neither _apply_tile_action nor _apply_shed_action alone can resolve, so
    it gets its own dedicated function.

    Args:
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place;
            "inventories" and "shed" are read/written.
        index: Which unit is acting: 0 for the farmer, i + 1 for hand i.
        pos: [x, y] board position of the acting unit, or None.
        item: The item being placed.
        n: How many of item to move into the shed (ignored for the
            animal-placement variant, which always places exactly 1).

    Returns:
        None. If the unit stands on an unoccupied COOP/PASTURE that item
        matches (GOOSE on a COOP, COW/SHEEP on a PASTURE) and the unit
        carries at least 1: sets tile["animal"] = item ("n" ignored,
        "standing on a matching unoccupied structure ... places one animal
        from inventory onto the tile") and decrements the unit's inventory
        by 1, deleting the key at 0. placed_day is left untouched, matching
        _new_structure_tile's existing deferral — no test exercises it yet.
        Otherwise (shed-drop variant): moves up to n of item from the
        unit's inventory into private["shed"] (created if absent), capped
        by the shed's remaining room under _SHED_CAPACITY same as DROP,
        deleting the inventory key at 0. Shed-adjacency is not re-checked
        here, matching _apply_shed_action's existing convention: only a
        unit _possible_actions already deemed shed-adjacent is ever offered
        this variant.
    """
    inventories = private.get("inventories")
    if not inventories or index >= len(inventories):
        return
    inventory = inventories[index]
    tile = _tile_at(farm, pos)
    if (isinstance(tile, dict) and tile.get("kind") in _STRUCTURE_ANIMALS
            and tile.get("animal") is None and item in _STRUCTURE_ANIMALS[tile["kind"]]
            and inventory.get(item, 0) > 0):
        tile["animal"] = item
        moved = 1
    else:
        shed = private.setdefault("shed", {})
        room = _SHED_CAPACITY - sum(shed.values())
        moved = max(0, min(n, inventory.get(item, 0), room))
        if moved:
            shed[item] = shed.get(item, 0) + moved
    if moved:
        left = inventory.get(item, 0) - moved
        if left > 0:
            inventory[item] = left
        else:
            inventory.pop(item, None)


def _apply_harvest(farm, private, index, pos):
    """Apply one unit's HARVEST action, crediting its inventory when it has an effect.

    python-kit/README.md, "HARVEST": harvesting a plant or an animal
    structure both clears/resets a farm tile *and* credits the unit's
    private inventory together — the same "needs farm and private
    together" situation _apply_place already handles for PLACE, so
    HARVEST gets its own dedicated function too, called directly from
    _apply_unit_action's dispatch instead of falling through to the
    _apply_tile_action + _apply_shed_action pair.

    Args:
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place;
            "inventories" is read/written.
        index: Which unit is acting: 0 for the farmer, i + 1 for hand i.
        pos: [x, y] board position of the acting unit, or None.

    Returns:
        None. Reproduces _apply_tile_action's former HARVEST tile-mutation
        exactly and unconditionally: on a PLANT tile, clears it to None
        when its crop has no subsequent yields (_ONE_TIME_CROPS), otherwise
        (ongoing crops TOMATO/STRAWBERRY) resets yield_units to 0; on a
        COOP/PASTURE, resets yield_units to 0 regardless of whether it
        carries an animal. Before mutating, captures the tile's yield_units
        and resolves the harvested product — the crop name for a PLANT
        tile, or _ANIMAL_PRODUCTS[tile["animal"]] for a structure tile
        (EGG/MILK/WOOL, not GOOSE/COW/SHEEP) — then, only when there's an
        inventories list for this unit, a resolvable product, and a
        positive captured yield_units, adds that many units of the product
        to the unit's inventory. An empty COOP/PASTURE (no animal) credits
        nothing, same as a tile that isn't a PLANT or animal structure;
        both still leave the farm untouched, matching _apply_tile_action's
        prior behavior.
    """
    tile = _tile_at(farm, pos)
    if not isinstance(tile, dict):
        return
    kind = tile.get("kind")
    if kind == "PLANT":
        product = tile.get("crop")
        units = tile.get("yield_units", 0)
        if product in _ONE_TIME_CROPS:
            _set_tile(farm, pos, None)
        else:
            tile["yield_units"] = 0
    elif kind in _STRUCTURE_ANIMALS:
        product = _ANIMAL_PRODUCTS.get(tile.get("animal"))
        units = tile.get("yield_units", 0)
        tile["yield_units"] = 0
    else:
        return
    if not product or units <= 0:
        return
    inventories = private.get("inventories")
    if not inventories or index >= len(inventories):
        return
    inventory = inventories[index]
    inventory[product] = inventory.get(product, 0) + units


def _apply_tile_action(farm, pos, action, day):
    """Apply one unit's action to the tile it stands on, if it has an effect.

    Dispatches on the tile's kind first (mirroring _base_actions), then on
    the action, so each newly-supported action lands inside the branch for
    the kind it already applies to.

    Args:
        farm: The acting player's farm dict, mutated in place.
        pos: [x, y] board position of the acting unit, or None.
        action: The unit's chosen action for this turn.
        day: The current in-game day, used to date FERTILIZE's bonus window.

    Returns:
        None. On a WEED tile: "DIG" clears it to None. On a PLANT tile:
        "WATER" marks it watered for today; "FERTILIZE" sets
        fertilized_until_day to day + 2, a 3-day bonus window starting today
        (python-kit/README.md); "DIG" clears it to None regardless of yield
        state. On a COOP/PASTURE: "DIG" clears it to None — the documented
        no-op for a structure with an animal on it (python-kit/README.md)
        is deferred, since no test exercises it yet. "FEED" marks it
        fed_today for the day — the matching WHEAT deduction is applied
        separately by _apply_shed_action, since this function has no
        access to private inventories. "CARE" marks it cared_today for the
        day; the yield bonus it banks is applied separately by
        _day_refresh, at end of day. On an empty tile: "BUILD_COOP"/
        "BUILD_PASTURE" writes a freshly-placed COOP/PASTURE tile
        (_new_structure_tile). Planting a seed (_apply_plant), PLACE
        (_apply_place) and HARVEST (_apply_harvest) are handled by their
        own dedicated functions instead of here, since each needs private
        inventory access this function doesn't have. Every other
        tile-kind/action combination is deferred to later tests, per the
        walking-skeleton approach.
    """
    tile = _tile_at(farm, pos)
    if tile is None:
        if action == "BUILD_COOP":
            _set_tile(farm, pos, _new_structure_tile("COOP"))
        elif action == "BUILD_PASTURE":
            _set_tile(farm, pos, _new_structure_tile("PASTURE"))
        return
    if not isinstance(tile, dict):
        return
    kind = tile.get("kind")
    if kind == "WEED":
        if action == "DIG":
            _set_tile(farm, pos, None)
    elif kind == "PLANT":
        if action == "WATER":
            tile["watered_today"] = True
        elif action == "FERTILIZE":
            tile["fertilized_until_day"] = day + 2
        elif action == "DIG":
            _set_tile(farm, pos, None)
    elif kind in _STRUCTURE_ANIMALS:
        if action == "DIG":
            _set_tile(farm, pos, None)
        elif action == "FEED":
            tile["fed_today"] = True
        elif action == "CARE":
            tile["cared_today"] = True
        elif action == "COLLECT_FERTILIZER":
            tile["fertilizer_available"] = False


def _apply_shed_action(private, index, action):
    """Apply one unit's private-inventory-facing action, if it has an effect.

    Mirrors _apply_tile_action's dispatch shape, but for actions that touch
    the private inventories/shed rather than a farm tile.

    Args:
        private: The player's private state, mutated in place; "inventories"
            (indexed [farmer, hand0, hand1, ...]) and "shed" are read/written.
        index: Which unit is acting: 0 for the farmer, i + 1 for hand i.
        action: The unit's chosen action for this turn.

    Returns:
        None. "DROP" moves every item in the unit's inventory into
        private["shed"] (created if absent), each item capped by the shed's
        remaining room under _SHED_CAPACITY with any excess discarded outright
        (python-kit/README.md), then empties the unit's inventory entirely.
        "FEED" deducts _FEED_WHEAT_COST WHEAT from the unit's inventory; the
        matching fed_today flag on the tile is set separately by
        _apply_tile_action, which has access to the farm but not private.
        "COLLECT_FERTILIZER" adds 1 FERTILIZER to the unit's inventory; the
        matching fertilizer_available flag is cleared separately by
        _apply_tile_action, for the same reason. ["PICKUP", item, n] moves
        up to n of item (default 1) from private["shed"] into the unit's
        inventory. Shed-adjacency is not re-checked here: _possible_actions
        only ever offers DROP/PICKUP to a unit already standing beside the
        shed; likewise FEED's WHEAT-availability and COLLECT_FERTILIZER's
        fertilizer_available preconditions are only checked by
        _possible_actions, not re-validated here. Every other action is
        deferred to later tests.
    """
    is_pickup = isinstance(action, list) and action[:1] == ["PICKUP"]
    if action not in ("DROP", "FEED", "COLLECT_FERTILIZER") and not is_pickup:
        return
    inventories = private.get("inventories")
    if not inventories or index >= len(inventories):
        return
    if action == "DROP":
        shed = private.setdefault("shed", {})
        room = _SHED_CAPACITY - sum(shed.values())
        for item, count in inventories[index].items():
            added = max(0, min(count, room))
            if added:
                shed[item] = shed.get(item, 0) + added
                room -= added
        inventories[index] = {}
    elif action == "FEED":
        inventory = inventories[index]
        inventory["WHEAT"] = inventory.get("WHEAT", 0) - _FEED_WHEAT_COST
    elif action == "COLLECT_FERTILIZER":
        inventory = inventories[index]
        inventory["FERTILIZER"] = inventory.get("FERTILIZER", 0) + 1
    elif is_pickup:
        item = action[1]
        n = action[2] if len(action) > 2 else 1
        shed = private.setdefault("shed", {})
        available = shed.get(item, 0)
        moved = max(0, min(n, available))
        if moved:
            inventory = inventories[index]
            inventory[item] = inventory.get(item, 0) + moved
            left = available - moved
            if left > 0:
                shed[item] = left
            else:
                shed.pop(item, None)


def _hire_spawn(farm):
    """Pick the spawn position for a newly-hired hand.

    python-kit/README.md, "Hiring": "A hired hand appears orthogonally
    adjacent to the shed in a free space following NWSE. If there are not
    open spaces, it looks for the one with the least occupants, breaking
    ties by NWSE preference." Both rules collapse into one: pick the
    shed-adjacent cell with the fewest current occupants, ties broken by
    NWSE order — a free cell simply has an occupant count of 0.

    Args:
        farm: The acting player's farm dict; "farmer" and "hands" are read.

    Returns:
        A new [x, y], one of (4,4)/(5,4)/(4,5)/(5,5) (NW/NE/SW/SE), chosen
        as above. Spawn placement ignores whether the cell's quadrant is
        locked (README.md): a hand can spawn on a locked tile and walk off
        it later.
    """
    order = [(4, 4), (5, 4), (4, 5), (5, 5)]
    occupants = [tuple(p) for p in [farm.get("farmer")] + list(farm.get("hands") or []) if p is not None]
    counts = [occupants.count(cell) for cell in order]
    return list(order[min(range(len(order)), key=lambda i: counts[i])])


def _apply_hire(farm):
    """Apply a HIRE market order.

    Args:
        farm: The acting player's farm dict, mutated in place.

    Returns:
        None. Appends a new hand to farm["hands"] at _hire_spawn's chosen
        position, deducts _hire_cost(hires_today) from money (priced
        before incrementing, since the cost is for "the number of hires
        already made today" — python-kit/README.md "Hiring"), then
        increments hires_today.
    """
    cost = _hire_cost(farm.get("hires_today", 0))
    spawn = _hire_spawn(farm)
    farm.setdefault("hands", []).append(spawn)
    farm["money"] = farm.get("money", 0) - cost
    farm["hires_today"] = farm.get("hires_today", 0) + 1


def _apply_buy_land(farm):
    """Apply a BUY_LAND market order.

    Args:
        farm: The acting player's farm dict, mutated in place.

    Returns:
        None. No-op once every quadrant is already unlocked. Otherwise
        unlocks the next quadrant in fixed order NW -> NE -> SW -> SE
        (python-kit/AGENTS.md: "the other three (NE, SW, SE) can be bought
        via BUY_LAND for $1k / $2k / $4k respectively") by appending its
        name to unlocked_quadrants and clearing every "LOCKED" tile in that
        quadrant's 5x5 block to None, then deducts
        _land_cost(unlocked-before-this-call) from money.
    """
    unlocked = farm.get("unlocked_quadrants") or []
    cost = _land_cost(unlocked)
    if cost is None:
        return
    next_quadrant = _QUADRANT_ORDER[len(set(unlocked))]
    farm.setdefault("unlocked_quadrants", []).append(next_quadrant)
    farm["money"] = farm.get("money", 0) - cost
    x0 = 5 if "E" in next_quadrant else 0
    y0 = 5 if next_quadrant.startswith("S") else 0
    tiles = farm.get("tiles") or []
    for y in range(y0, min(y0 + 5, len(tiles))):
        row = tiles[y]
        for x in range(x0, min(x0 + 5, len(row))):
            if row[x] == "LOCKED":
                row[x] = None


def _apply_buy_seed(farm, private, crop, n):
    """Apply a BUY_SEED market order: fixed price, unlimited supply.

    Args:
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place; "seeds" is
            credited.
        crop: The crop to buy, a key of _SEED_COSTS.
        n: How many seeds to buy.

    Returns:
        None. Credits private["seeds"][crop] by n and deducts
        _SEED_COSTS[crop] * n from money.
    """
    seeds = private.setdefault("seeds", {})
    seeds[crop] = seeds.get(crop, 0) + n
    farm["money"] = farm.get("money", 0) - _SEED_COSTS[crop] * n


def _apply_buy_animal(farm, private, animal, n):
    """Apply a BUY_ANIMAL market order: fixed price, unlimited supply.

    Args:
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place; "shed" is
            credited.
        animal: The animal to buy, a key of _ANIMAL_COSTS.
        n: How many animals to buy.

    Returns:
        None. Bought animals go straight to private["shed"][animal]
        (credited by n), and _ANIMAL_COSTS[animal] * n is deducted from
        money.
    """
    shed = private.setdefault("shed", {})
    shed[animal] = shed.get(animal, 0) + n
    farm["money"] = farm.get("money", 0) - _ANIMAL_COSTS[animal] * n


def _apply_buy_product(state, farm, private, item, n):
    """Apply a BUY_PRODUCT market order: dynamic price, drains market inventory.

    Args:
        state: The forward-simulated state, mutated in place;
            state["market"]["inventory"] is read/written.
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place; "shed" is
            credited.
        item: The product to buy ("WHEAT" or "FERTILIZER" — the only two
            products BUY_PRODUCT supports, python-kit/README.md "Buying
            inventory from the market").
        n: How many units to buy.

    Returns:
        None. Buys up to n units one at a time (python-kit/README.md:
        orders are "processed... one unit at a time"), each priced by
        _price at that unit's post-buy inventory, stopping early once
        money runs out ("If a player runs out of money mid-order, the
        order is stopped"). Each bought unit credits private["shed"][item]
        by 1, deducts its price from money, and decrements
        state["market"]["inventory"][item] by 1 (documented as drained by
        BUY_PRODUCT orders). state["market"]["prices"] is left stale —
        untested, deferred.
    """
    inventory = state.setdefault("market", {}).setdefault("inventory", {})
    shed = private.setdefault("shed", {})
    for _ in range(n):
        inv = inventory.get(item, _MARKET_I0) - 1
        price = _price(item, inv)
        if farm.get("money", 0) < price:
            break
        farm["money"] = farm.get("money", 0) - price
        inventory[item] = inv
        shed[item] = shed.get(item, 0) + 1


def _apply_sell(state, farm, private, item, n):
    """Apply a SELL market order: dynamic price, grows market inventory.

    Args:
        state: The forward-simulated state, mutated in place;
            state["market"]["inventory"] is read/written.
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place; "shed" is
            debited.
        item: The product to sell; any resource in _MARKET_PARAMS
            (python-kit/README.md: "every product, including fertilizer
            collected from animals, can be sold via SELL").
        n: How many units to sell.

    Returns:
        None. Sells up to n units from private["shed"][item] one at a time,
        stopping early once the shed runs out. Each unit is priced by
        _price at that unit's pre-sell inventory ("the sell price is
        quoted at the pre-sell inventory"), credits the price to money, and
        debits the shed by 1, deleting the key at 0. Grows
        state["market"]["inventory"][item] by 1 per unit sold, except when
        the price has been driven to the $1 floor: "the unit is still
        purchased but is not added to market inventory, so the floor
        remains responsive to subsequent buys."
    """
    inventory = state.setdefault("market", {}).setdefault("inventory", {})
    shed = private.setdefault("shed", {})
    for _ in range(n):
        have = shed.get(item, 0)
        if have <= 0:
            break
        inv = inventory.get(item, _MARKET_I0)
        price = _price(item, inv)
        left = have - 1
        if left > 0:
            shed[item] = left
        else:
            shed.pop(item, None)
        farm["money"] = farm.get("money", 0) + price
        if price > _PRICE_FLOOR:
            inventory[item] = inv + 1


def _apply_market_order(state, farm, private, order):
    """Dispatch one market order from action_dict["market"] to its handler.

    Args:
        state: The forward-simulated state, mutated in place.
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place.
        order: One market order, e.g. ["HIRE"], ["BUY_SEED", "CARROT", 1].

    Returns:
        None. Dispatches by order[0] to _apply_hire, _apply_buy_land,
        _apply_buy_seed, _apply_buy_animal, _apply_buy_product or
        _apply_sell, defaulting a missing quantity argument to 1. Every
        other or malformed order is a no-op — no precondition (affordability,
        land already fully bought, etc.) is re-validated here, matching
        _apply_shed_action's existing convention that _possible_actions is
        solely responsible for offering only legal orders.
    """
    if not order:
        return
    verb, args = order[0], order[1:]
    if verb == "HIRE":
        _apply_hire(farm)
    elif verb == "BUY_LAND":
        _apply_buy_land(farm)
    elif verb == "BUY_SEED" and args:
        _apply_buy_seed(farm, private, args[0], args[1] if len(args) > 1 else 1)
    elif verb == "BUY_ANIMAL" and args:
        _apply_buy_animal(farm, private, args[0], args[1] if len(args) > 1 else 1)
    elif verb == "BUY_PRODUCT" and args:
        _apply_buy_product(state, farm, private, args[0], args[1] if len(args) > 1 else 1)
    elif verb == "SELL" and args:
        _apply_sell(state, farm, private, args[0], args[1] if len(args) > 1 else 1)


def _apply_decay(farm, day):
    """Decay one-time crops past their max lifespan (python-kit/README.md L126-127).

    Args:
        farm: The acting player's farm dict, mutated in place; "tiles" is
            scanned for PLANT tiles.
        day: The current in-game day (this must run every turn, not just at
            day rollover — python-kit/README.md doesn't gate decay on the
            day-refresh boundary, and tests/test_apply_action.py's
            test_plant_turning_to_weed_by_decay exercises it mid-day).

    Returns:
        None. Each tile is visited at most once, keyed by id() (mirroring
        _clone_state's/_day_refresh's memo, for the same aliased-grid-row
        reason). A one-time crop (_ONE_TIME_CROPS) whose age
        (day - planted_day) has reached max_lifespan_left loses 1
        yield_units; once yield_units hits 0 the tile becomes a weed.
        Ongoing crops (max_lifespan_left == -1, the existing sentinel) are
        untouched — no test yet exercises their production-count-based
        decay. The "every other turn" decrement cadence (python-kit/
        README.md L126) is also not exercised by the one given test, so
        this decrements every call once the threshold is reached; deferred
        like _day_refresh already defers its own unexercised sub-rules.
    """
    seen = set()
    for row in farm.get("tiles") or []:
        for x, tile in enumerate(row):
            if not isinstance(tile, dict) or id(tile) in seen:
                continue
            seen.add(id(tile))
            if tile.get("kind") != "PLANT" or tile.get("crop") not in _ONE_TIME_CROPS:
                continue
            lifespan = tile.get("max_lifespan_left", -1)
            if lifespan < 0 or day - tile.get("planted_day", 0) < lifespan:
                continue
            units = tile.get("yield_units", 0) - 1
            if units <= 0:
                row[x] = {"kind": "WEED"}
            else:
                tile["yield_units"] = units


def _apply_town_consumption(state, hour, day):
    """Drain market inventory for town-center demand (python-kit/README.md L173, L360).

    Args:
        state: The forward-simulated state, mutated in place; "market" (and
            its "inventory" sub-dict) is created on demand.
        hour: The turn's hour-of-day before this turn's increment.
        day: The turn's day before this turn's increment.

    Returns:
        None. Every _MARKET_PARAMS resource except FERTILIZER loses 1 unit
        of market inventory whenever hour is a multiple of
        _TOWN_CENTER_SELL_INTERVAL (i.e. once per day, at hour 0) — the town
        center "consumes one of every product (excluding fertilizer)"
        (python-kit/README.md L173), a flat rate that "does not ramp". Each
        shop name in state["town"]["unlocked_shops"] (duplicates consume
        independently, python-kit/README.md L169-171) drains its own
        _SHOP_DEMAND items whenever the absolute turn count is 1 modulo
        _TOWN_SHOP_SELL_INTERVAL — an offset from the town center's own
        modulo-24 tick chosen to match tests/test_apply_action.py's
        test_town_shop_consumption (turn 97 = day 4 hour 1); only inferred
        from that one case, not stated explicitly in python-kit/README.md,
        which merely says shops consume "every townShopSellInterval turns".
    """
    inventory = state.setdefault("market", {}).setdefault("inventory", {})
    if hour % _TOWN_CENTER_SELL_INTERVAL == 0:
        for item in _MARKET_PARAMS:
            if item != "FERTILIZER":
                inventory[item] = inventory.get(item, _MARKET_I0) - 1
    turn = day * _TURNS_PER_DAY + hour
    if turn % _TOWN_SHOP_SELL_INTERVAL == 1:
        for shop in state.get("town", {}).get("unlocked_shops", []):
            for item, count in _SHOP_DEMAND.get(shop, {}).items():
                inventory[item] = inventory.get(item, _MARKET_I0) - count


def _day_refresh(farm, weeds_enabled=True, seed=None):
    """Update plant/animal condition for a new day at the day-rollover boundary.

    Args:
        farm: The acting player's farm dict, mutated in place; "tiles" is
            scanned for PLANT and occupied COOP/PASTURE tiles.
        weeds_enabled: Test/implementation-controllability switch, not a
            gameplay parameter — python-kit/README.md's weed-spawn rule
            (L357) is unconditional. When False, skips the per-empty-tile
            random weed-spawn roll below entirely, leaving every other rule
            in this function (animal escape/fertilizer, plant-to-weed decay)
            untouched. Defaults to True so existing callers see no change.
        seed: Test/implementation-controllability switch, not a gameplay
            parameter. When not None, the per-empty-tile weed-spawn rolls
            are drawn from a local random.Random(seed) instance instead of
            the global random module, giving a caller a reproducible roll
            sequence. Defaults to None, which preserves today's behavior.

    Returns:
        None. Each tile is visited at most once, keyed by id() (mirroring
        _clone_state's memo), since a test fixture's aliased grid rows can
        otherwise repeat the same tile object across several "rows".

        For an occupied animal-structure tile: pending_care_bonus banks +1
        when both fed_today and cared_today are true (python-kit/README.md
        L75-80); consecutive_unfed resets to 0 when fed_today, or increments
        by 1 otherwise (python-kit/README.md L111-115, L320); fed_today and
        cared_today both reset to False for the new day (python-kit/README.md
        L243's fed/watered reset, extended to cared_today since CARE is
        documented as once-per-day, L71). If the incremented consecutive_unfed
        reaches 2, the animal escapes: the tile is replaced with
        _new_structure_tile(kind), resetting animal/fed/unfed/cared/
        fertilizer/bonus to their just-built defaults (python-kit/README.md
        "Watering / Animal Feed": "they escape and be unrecoverable").
        Otherwise, the animal survives the day and fertilizer_available is
        set True unconditionally — "every surviving animal makes 1
        available at the end of each day, whether or not it was fed or
        cared for" (python-kit/README.md L70); uncollected fertilizer
        doesn't accumulate, so setting an already-True flag again is a
        harmless no-op (L70: "does not accumulate").

        For a PLANT tile: consecutive_unwatered resets to 0 when
        watered_today, or increments by 1 otherwise; watered_today resets to
        False either way. If the incremented consecutive_unwatered reaches 2,
        the plant turns to a weed: the tile is replaced with {"kind": "WEED"}
        (python-kit/README.md "Watering / Animal Feed": "left unwatered for
        two consecutive days, at the end of the day they turn into a WEED").

        Separately, unless weeds_enabled is False, every empty (None) tile
        has an independent _WEED_SPAWN_CHANCE probability of spawning a
        weed this rollover ("every empty unlocked tile has a
        weedSpawnChance ... of spawning a weed at end-of-day",
        python-kit/README.md L357/AGENTS.md L19) — a genuine random.random()
        roll per the user's instruction, not a deterministic formula, drawn
        from random.Random(seed) when seed is given or else from the global
        random module. This makes tests/test_apply_action.py's
        test_random_weed_spawn_chance inherently flaky unless it fixes a
        seed; it hard-codes one exact resulting weed tile, which an
        unseeded roll will only reproduce by chance.
    """
    seen = set()
    tiles = farm.get("tiles") or []
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict) or id(tile) in seen:
                continue
            seen.add(id(tile))
            kind = tile.get("kind")
            if kind in _STRUCTURE_ANIMALS and tile.get("animal") is not None:
                if tile.get("fed_today") and tile.get("cared_today"):
                    tile["pending_care_bonus"] = tile.get("pending_care_bonus", 0) + 1
                if tile.get("fed_today"):
                    tile["consecutive_unfed"] = 0
                else:
                    tile["consecutive_unfed"] = tile.get("consecutive_unfed", 0) + 1
                tile["fed_today"] = False
                tile["cared_today"] = False
                if tile["consecutive_unfed"] >= 2:
                    row[x] = _new_structure_tile(kind)
                else:
                    tile["fertilizer_available"] = True
            elif kind == "PLANT":
                if tile.get("watered_today"):
                    tile["consecutive_unwatered"] = 0
                else:
                    tile["consecutive_unwatered"] = tile.get("consecutive_unwatered", 0) + 1
                tile["watered_today"] = False
                if tile["consecutive_unwatered"] >= 2:
                    row[x] = {"kind": "WEED"}
    if weeds_enabled:
        rng = random.Random(seed) if seed is not None else random
        for row in tiles:
            for x, tile in enumerate(row):
                if tile is None and rng.random() < _WEED_SPAWN_CHANCE:
                    row[x] = {"kind": "WEED"}


def _unit_action(entry):
    """Extract one unit's chosen action from its action-list entry.

    Farmer entries are always a 1-element list wrapping the action itself,
    either a bare string ("PASS") or a parameterized list (["PLANT",
    "CARROT"]). Hand entries follow the same convention when the action
    takes no argument (["PASS"]), but a parameterized hand action is flat
    instead of double-wrapped (["PLANT", "CARROT"], not [["PLANT",
    "CARROT"]]).

    Args:
        entry: One unit's action-list entry from action_dict["farmer"] or
            action_dict["hands"][i].

    Returns:
        entry[0] when entry has exactly one element (unwraps both a bare
        no-arg action and a farmer's wrapped parameterized action);
        otherwise entry itself (a flat parameterized hand action).
    """
    return entry[0] if len(entry) == 1 else entry


def _plant_allowed_crops(seeds, farmer_action, hand_actions):
    """Which crops may be planted this turn under the all-or-nothing rule.

    python-kit/README.md, "Plants": "If you try to plant too many in a
    specific turn, none are planted - ie if you have 1 melon seed, but two
    units do the PLANT MELON command." This tallies demand per crop across
    every unit's chosen action before any of them are applied.

    Args:
        seeds: private["seeds"], {crop: count} in stock.
        farmer_action: The farmer's parsed action (_unit_action's result),
            or None.
        hand_actions: The hands' parsed actions (_unit_action's results),
            one per hand, None where a hand has no action this turn.

    Returns:
        The set of crops for which every simultaneous PLANT this turn may
        proceed: a crop is allowed only when seeds[crop] covers the total
        number of units planting it this turn; a crop with insufficient
        seed is entirely excluded, blocking all of its PLANTs this turn.
    """
    demand = {}
    for action in [farmer_action] + list(hand_actions):
        if isinstance(action, list) and len(action) == 2 and action[0] == "PLANT":
            crop = action[1]
            demand[crop] = demand.get(crop, 0) + 1
    return {crop for crop, need in demand.items() if seeds.get(crop, 0) >= need}


def _apply_unit_action(farm, private, index, pos, action, day, plant_allowed):
    """Apply one unit's parsed action and return its post-action position.

    Args:
        farm: The acting player's farm dict, mutated in place.
        private: The player's private state, mutated in place.
        index: Which unit is acting: 0 for the farmer, i + 1 for hand i.
        pos: [x, y] board position of the acting unit.
        action: The unit's parsed action (_unit_action's result): a bare
            string, or a [verb, *args] list.
        day: The current in-game day.
        plant_allowed: The set of crops this turn's PLANT actions may
            proceed for (_plant_allowed_crops's result).

    Returns:
        The unit's new [x, y] position (_move's result — a no-op for
        PLACE/PLANT/HARVEST, none of which are movement actions). PLACE
        dispatches to _apply_place; PLANT dispatches to _apply_plant only
        when its crop is in plant_allowed; HARVEST dispatches to
        _apply_harvest; every other action falls through to the existing
        _apply_tile_action + _apply_shed_action pair.
    """
    verb = action[0] if isinstance(action, list) else action
    if verb == "PLACE":
        item = action[1]
        n = action[2] if len(action) > 2 else 1
        _apply_place(farm, private, index, pos, item, n)
    elif verb == "PLANT":
        crop = action[1]
        if crop in plant_allowed:
            _apply_plant(farm, private, pos, crop, day)
    elif verb == "HARVEST":
        _apply_harvest(farm, private, index, pos)
    else:
        _apply_tile_action(farm, pos, action, day)
        _apply_shed_action(private, index, action)
    return _move(pos, action)


def _apply_action(obs, action_dict, weeds_enabled=True, seed=None):
    """Advance one player's forward-simulated turn by one hour.

    Applies this step's chosen action to the acting player's farmer and each
    hired hand, then this turn's market orders, then advances the turn
    clock. Handles PASS, the four movement directions, WATER, FERTILIZE,
    HARVEST, DIG, DROP, FEED, COLLECT_FERTILIZER, PICKUP, PLACE, PLANT
    (gated by the all-or-nothing simultaneous-planting rule), and the market
    orders HIRE, BUY_LAND, BUY_SEED, BUY_PRODUCT, BUY_ANIMAL and SELL (capped
    at _MAX_MARKET_ORDERS_PER_TURN, extras silently dropped per python-kit/
    README.md L94/L354), the town center's and every unlocked town shop's
    market-inventory drain (_apply_town_consumption), one-time crops' post-
    max-lifespan yield decay (_apply_decay), plus day-rollover's animal-
    escaping/weed-conversion/consecutive-unfed/fertilizer_available/random-
    weed-spawn updates (_day_refresh). Still deferred, per the walking-
    skeleton approach: cross-player concurrent market processing (this
    function only ever simulates the acting player's own turn), ongoing
    crops' production-count-based decay, and market "prices" refresh
    (BUY_PRODUCT/SELL update "inventory" but leave "prices" stale).

    Args:
        obs: The observation dict for the current turn; left unchanged.
        action_dict: {"farmer": [...], "hands": [[...], ...], "market": [...]},
            each unit list holding its one chosen action for this turn.
        weeds_enabled: Forwarded to _day_refresh's same-named parameter;
            test/implementation-controllability only, not a gameplay
            parameter — defaults to True (today's behavior unchanged).
        seed: Forwarded to _day_refresh's same-named parameter;
            test/implementation-controllability only, not a gameplay
            parameter — defaults to None (today's behavior unchanged).

    Returns:
        A new state, mutated per the actions described above, with "hour"
        advanced by one, rolling "day" over (and running _day_refresh) once
        "hour" reaches _TURNS_PER_DAY.
    """
    state = _clone_state(obs)
    farms = state.get("farms", [])
    player = state.get("player", 0)
    farm = farms[player] if player < len(farms) else {}
    private = state.get("private", {})

    day = state.get("day", 0)
    hour = state.get("hour", 0)

    farmer_entry = action_dict.get("farmer") or []
    hand_entries = action_dict.get("hands") or []
    farmer_action = _unit_action(farmer_entry) if farmer_entry else None
    hand_actions = [_unit_action(entry) if entry else None for entry in hand_entries]
    plant_allowed = _plant_allowed_crops(private.get("seeds", {}), farmer_action, hand_actions)

    if farmer_entry and farm.get("farmer") is not None:
        farm["farmer"] = _apply_unit_action(farm, private, 0, farm["farmer"], farmer_action, day, plant_allowed)

    hands = farm.get("hands", [])
    for i, hand_action in enumerate(hand_actions):
        if hand_entries[i] and i < len(hands):
            hands[i] = _apply_unit_action(farm, private, i + 1, hands[i], hand_action, day, plant_allowed)

    for order in (action_dict.get("market") or [])[:_MAX_MARKET_ORDERS_PER_TURN]:
        _apply_market_order(state, farm, private, order)

    _apply_town_consumption(state, hour, day)
    _apply_decay(farm, day)

    hour += 1
    if hour >= _TURNS_PER_DAY:
        hour = 0
        state["day"] = state.get("day", 0) + 1
        _day_refresh(farm, weeds_enabled=weeds_enabled, seed=seed)
    state["hour"] = hour

    return state


def _get_reward(state):
    """Score a terminal state from the acting player's perspective.

    Args:
        state: The observation dict for the current turn; reads "player" and
            (via _is_terminal) "day"/"hour", plus each farm's "money".

    Returns:
        The acting player's money minus the opponent's, once the season has
        ended (_is_terminal(state) is True); 0 while the game is ongoing,
        since python-kit/README.md L248-254 only scores the final tally.
    """
    if not _is_terminal(state):
        return 0
    farms = state.get("farms", [])
    player = state.get("player", 0)
    opponent = 1 - player
    return farms[player].get("money", 0) - farms[opponent].get("money", 0)
