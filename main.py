#!/usr/bin/env python3
__all__ = ["laziest_farmer", "_opponent_tracker"]


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
    previous = {} if obs.get("step") == 1 else _opponent_cache
    _opponent_cache = current
    return {**current, "prev_money": previous.get("money", current.get("money"))}
