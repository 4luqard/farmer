#!/usr/bin/env python3
import json
import os

__all__ = ["laziest_farmer", "_opponent_tracker"]


# ---- Farmer agent ----

def laziest_farmer(obs):
    # Buy one wheat seed on the very first turn, then PASS forever after.
    if obs.get("step", 0) == 0:
        return {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}
    return {"farmer": ["PASS"], "hands": [], "market": []}


# ---- Opponent tracking ----

_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opponent_cache.json")


def _load_cache() -> dict:
    try:
        with open(_CACHE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_cache(data) -> None:
    with open(_CACHE_PATH, "w") as f:
        json.dump(data, f)


def _opponent_tracker(obs) -> dict:
    current = obs["farms"][1 - obs["player"]]
    previous = _load_cache()
    _save_cache(current)
    return {**current, "prev_money": previous.get("money")}
