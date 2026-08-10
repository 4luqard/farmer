#!/usr/bin/env python3
__all__ = ["_opponent_tracker"]


def _opponent_tracker(obs) -> dict:
    return obs["farms"][1 - obs["player"]]
