#!/usr/bin/env python3
__all__ = ["laziest_farmer", "_opponent_tracker", "_possible_actions", "_clone_state", "_is_terminal", "_apply_action"]


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
_ALL_QUADRANTS = {"NW", "NE", "SW", "SE"}
_SEED_COSTS = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_FIRST_YIELD_DAY = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
_ONE_TIME_CROPS = {"WHEAT", "CARROT", "MELON"}  # python-kit/README.md Object Types table
_ANIMAL_COSTS = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_LAND_COSTS = [1000, 2000, 4000]
_MARKET_I0 = 10000
_PRICE_FLOOR = 1
_MARKET_PARAMS = {  # scarcity-side price curve, python-kit/README.md L222-232
    "WHEAT": {"base": 25, "T": 400, "func": "sqrt", "target": 0.80},
    "FERTILIZER": {"base": 100, "T": 200, "func": "linear", "target": 0.40},
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
        func: Curve name from _MARKET_PARAMS, "sqrt" or "linear".
        x: The curve input; negative values are clamped to 0.

    Returns:
        The square root of x for "sqrt", otherwise x itself — unknown names
        deliberately fall back to the linear curve.
    """
    x = max(0.0, x)
    return x ** 0.5 if func == "sqrt" else x  # "linear" + documented fallback


def _buy_price(item, inv):
    """BUY_PRODUCT unit price: the curve at post-buy inventory (python-kit/README.md L202-214)."""
    p = _MARKET_PARAMS[item]
    amp = p["target"] * p["base"] / _shape(p["func"], p["T"])
    return max(_PRICE_FLOOR, int(round(p["base"] + amp * _shape(p["func"], _MARKET_I0 - inv))))


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
        (python-kit/README.md); "HARVEST" clears the tile to None when its
        crop has no subsequent yields (_ONE_TIME_CROPS), and otherwise
        (ongoing crops TOMATO/STRAWBERRY) resets yield_units to 0; "DIG"
        clears it to None regardless of yield state. On a COOP/PASTURE:
        "HARVEST" resets yield_units to 0; "DIG" clears it to None — the
        documented no-op for a structure with an animal on it
        (python-kit/README.md) is deferred, since no test exercises it yet.
        Every other tile-kind/action combination is deferred to later tests,
        per the walking-skeleton approach.
    """
    tile = _tile_at(farm, pos)
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
        elif action == "HARVEST":
            if tile.get("crop") in _ONE_TIME_CROPS:
                _set_tile(farm, pos, None)
            else:
                tile["yield_units"] = 0
        elif action == "DIG":
            _set_tile(farm, pos, None)
    elif kind in _STRUCTURE_ANIMALS:
        if action == "HARVEST":
            tile["yield_units"] = 0
        elif action == "DIG":
            _set_tile(farm, pos, None)


def _apply_action(obs, action_dict):
    """Advance one player's forward-simulated turn by one hour.

    Applies this step's chosen action to the acting player's farmer and each
    hired hand, then advances the turn clock. Only PASS, the four movement
    directions, WATER, FERTILIZE, HARVEST, and DIG are handled so far — the
    rest of python-kit/README.md's "Turn Processing Order" (market orders,
    day refresh, price/income updates, ...) is deferred to later tests, per
    the walking-skeleton approach.

    Args:
        obs: The observation dict for the current turn; left unchanged.
        action_dict: {"farmer": [...], "hands": [[...], ...], "market": [...]},
            each unit list holding its one chosen action for this turn.

    Returns:
        A new state: the acting player's farmer and hands moved per their
        chosen action, and "hour" advanced by one, rolling "day" over once
        "hour" reaches _TURNS_PER_DAY.
    """
    state = _clone_state(obs)
    farms = state.get("farms", [])
    player = state.get("player", 0)
    farm = farms[player] if player < len(farms) else {}

    day = state.get("day", 0)

    farmer_action = action_dict.get("farmer") or []
    if farmer_action and farm.get("farmer") is not None:
        _apply_tile_action(farm, farm["farmer"], farmer_action[0], day)
        farm["farmer"] = _move(farm["farmer"], farmer_action[0])

    hands = farm.get("hands", [])
    for i, hand_action in enumerate(action_dict.get("hands", [])):
        if hand_action and i < len(hands):
            _apply_tile_action(farm, hands[i], hand_action[0], day)
            hands[i] = _move(hands[i], hand_action[0])

    hour = state.get("hour", 0) + 1
    if hour >= _TURNS_PER_DAY:
        hour = 0
        state["day"] = state.get("day", 0) + 1
    state["hour"] = hour

    return state
