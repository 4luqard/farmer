#!/usr/bin/env python3
__all__ = ["laziest_farmer", "_opponent_tracker", "_possible_actions"]


# ---- Farmer agent ----

def laziest_farmer(obs):
    # Buy one wheat seed on the very first turn, then PASS forever after.
    if obs.get("step", 0) == 0:
        return {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}
    return {"farmer": ["PASS"], "hands": [], "market": []}


# ---- Opponent tracking ----

_opponent_cache = {}  # in-memory only: resets on process start, i.e. per match


def _opponent_tracker(obs) -> dict:
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


def _apply_carried_inventory(actions, items):
    dropped = False
    for item, count in items.items():
        if count > 0:
            actions.append(["PLACE", item, count])
            dropped = True
    if dropped:
        actions.append("DROP")


def _quadrant(pos):
    x, y = pos
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _tile_unlocked(farm, pos):
    unlocked = farm.get("unlocked_quadrants")
    if unlocked is None or pos is None:
        return True
    return _quadrant(pos) in unlocked


def _base_actions(unlocked, seed):
    actions = ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]
    if unlocked:
        actions.extend(["WATER", "BUILD_COOP", "BUILD_PASTURE"])
        for crop, count in seed.items():
            if count > 0:
                actions.append(["PLANT", crop])
    return actions


def _possible_actions(obs) -> dict:
    seed = obs.get("private", {}).get("seed", {})

    farms = obs.get("farms", [])
    player = obs.get("player", 0)
    farm = farms[player] if player < len(farms) else {}
    hires_today = farm.get("hires_today", 0)

    farmer_pos = farm.get("farmer")
    hand_positions = farm.get("hands", [])
    hand_pos = hand_positions[0] if hand_positions else None

    farmer = _base_actions(_tile_unlocked(farm, farmer_pos), seed)
    hand = _base_actions(_tile_unlocked(farm, hand_pos), seed)

    market = [
        "HIRE", "BUY_LAND",
        ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
        ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
        ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
    ]

    shed_adjacent = tuple(farm.get("farmer", [])) in _SHED_ADJACENT

    if shed_adjacent:
        for item, count in obs.get("private", {}).get("shed", {}).items():
            for n in range(1, count + 1):
                farmer.append(["PICKUP", item, n])
                hand.append(["PICKUP", item, n])
                market.append(["SELL", item, n])

        carried = obs.get("private", {}).get("inventory", [])
        if carried:
            _apply_carried_inventory(farmer, carried[0])
            if len(carried) > 1:
                _apply_carried_inventory(hand, carried[1])

    if shed_adjacent and hires_today >= 1:
        hands = hand if hires_today == 1 else [list(hand) for _ in range(hires_today)]
    else:
        hands = [list(farmer) for _ in range(hires_today)]

    return {"farmer": farmer, "hands": hands, "market": market}
