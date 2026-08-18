#!/usr/bin/env python3
import pytest
import numpy as np
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import *

def test_possible_actions():
    # What actions the farmer can take in the first step
    assert _possible_actions({"step": 0}) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE"],
        "hands": [],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

    # When there is a seed
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 0}, {"hires_today": 1}],
        "private": {"seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"]],
        "hands": [],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }
    
    # When there is a hired hand
    assert _possible_actions({
        "player": 1,
        "farms": [{"hires_today": 0}, {"hires_today": 1}],
        "private": {"seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"]],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
