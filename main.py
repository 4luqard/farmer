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


def _possible_actions(obs) -> dict:
    farmer = ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "WATER", "BUILD_COOP", "BUILD_PASTURE"]
    for crop, count in obs.get("private", {}).get("seed", {}).items():
        if count > 0:
            farmer.append(["PLANT", crop])

    farms = obs.get("farms", [])
    player = obs.get("player", 0)
    farm = farms[player] if player < len(farms) else {}
    hires_today = farm.get("hires_today", 0)

    market = [
        "HIRE", "BUY_LAND",
        ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
        ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
        ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
    ]

    if tuple(farm.get("farmer", [])) in _SHED_ADJACENT:
        for item, count in obs.get("private", {}).get("shed", {}).items():
            if count > 0:
                farmer.append(["PICKUP", item, count])
                market.append(["SELL", item, count])

    hands = [list(farmer) for _ in range(hires_today)]

    return {"farmer": farmer, "hands": hands, "market": market}
