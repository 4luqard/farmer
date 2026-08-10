#!/usr/bin/env python3
import json
import os

__all__ = ["_opponent_tracker"]

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
