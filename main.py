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
_BOARD_SIZE = 10
_ANIMALS = {"GOOSE", "COW", "SHEEP"}
_STRUCTURE_ANIMALS = {"COOP": ("GOOSE",), "PASTURE": ("COW", "SHEEP")}


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


def _tile_at(farm, pos):
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


def _movement_actions(pos):
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


def _base_actions(unlocked, seed, pos=None, tile=None, carried=None):
    carried = carried or {}
    actions = _movement_actions(pos)
    if not unlocked:
        return actions
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        actions.append("DIG")
        return actions
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        watered = tile.get("watered_today", False)
        fertilized = tile.get("fertilized_until_day", -1) >= 0
        if not watered:
            actions.append("WATER")
        actions.append("DIG")
        if carried.get("FERTILIZER", 0) > 0 and not fertilized:
            actions.append("FERTILIZE")
        if tile.get("yield_units", 0) > 0:
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
    seed = obs.get("private", {}).get("seeds", {})

    farms = obs.get("farms", [])
    player = obs.get("player", 0)
    farm = farms[player] if player < len(farms) else {}
    hires_today = farm.get("hires_today", 0)

    farmer_pos = farm.get("farmer")
    hand_positions = farm.get("hands", [])
    carried = obs.get("private", {}).get("inventories", [])
    shed = obs.get("private", {}).get("shed", {})

    farmer = _base_actions(_tile_unlocked(farm, farmer_pos), seed, farmer_pos,
                            _tile_at(farm, farmer_pos), carried[0] if carried else None)

    market = [
        "HIRE", "BUY_LAND",
        ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
        ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
        ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
    ]
    for item in shed:
        if item not in _ANIMALS:
            market.append(["SELL", item, 1])

    shed_adjacent = tuple(farm.get("farmer", [])) in _SHED_ADJACENT

    if shed_adjacent:
        for item, count in shed.items():
            for n in range(1, count + 1):
                farmer.append(["PICKUP", item, n])
        if carried:
            _apply_carried_inventory(farmer, carried[0])

    hand_lists = []
    for i in range(hires_today):
        hand_pos = hand_positions[i] if i < len(hand_positions) else None
        hand_carried = carried[i + 1] if len(carried) > i + 1 else None
        hand = _base_actions(_tile_unlocked(farm, hand_pos), seed, hand_pos,
                             _tile_at(farm, hand_pos), hand_carried)
        if shed_adjacent:
            for item, count in shed.items():
                for n in range(1, count + 1):
                    hand.append(["PICKUP", item, n])
            if len(carried) > i + 1:
                _apply_carried_inventory(hand, carried[i + 1])
        hand_lists.append(hand)

    if shed_adjacent and hires_today == 1:
        hands = hand_lists[0]
    else:
        hands = hand_lists

    return {"farmer": farmer, "hands": hands, "market": market}
