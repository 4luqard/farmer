#!/usr/bin/env python3
import pytest
import numpy as np
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import *

def farm_tiles(unlocked_quadrants):
    if "SE" in unlocked_quadrants:
        return [[None] * 10] * 10
    elif "SW" in unlocked_quadrants:
        return [[None] * 10] * 5 + [[None] * 5 + ["LOCKED"] * 5] * 5
    elif "NE" in unlocked_quadrants:
        return [[None] * 10] * 5 + [["LOCKED"] * 10] * 5
    else:
        return [[None] * 5 + ["LOCKED"]] * 5 + [["LOCKED"] * 10] * 5

def weed_tile(y, x, unlocked_quadrants=['NW']):
    tiles = farm_tiles(unlocked_quadrants)
    tiles[y][x] = {"kind": "WEED"}
    return tiles

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

    # When there is a product in the shed
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 1, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"shed": {"WHEAT": 1}, "seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]],
        "hands": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
                   ["SELL", "WHEAT", 1]]
    }

    # When there is a product in the inventory of a farmer
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 0, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"inventory": [{"WHEAT": 1}], "seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "WHEAT", 1], "DROP"],
        "hands": [],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

    # When there is a product in the inventory of a farmer and hand
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 1, "farmer": [4, 4], "hands": [[5, 4]]}, {"hires_today": 1}],
        "private": {"inventory": [{"WHEAT": 1}, {"CARROT": 1}], "seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "WHEAT", 1], "DROP"],
        "hands": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "CARROT", 1], "DROP"],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

    # When the farmer or the hand is in a locked area
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 1, "farmer": [4, 4], "hands": [[5, 4]], "unlocked_quadrants": ["NW"]}, {"hires_today": 1}],
        "private": {"inventory": [{"WHEAT": 1}, {"CARROT": 1}], "seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "WHEAT", 1], "DROP"],
        "hands": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   ["PLACE", "CARROT", 1], "DROP"],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

    # When there are more than 1 hires
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"shed": {"WHEAT": 1}, "seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]],
                  ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
                   ["SELL", "WHEAT", 1]]
    }

    # When there are more than one item
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"shed": {"WHEAT": 3}, "seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1], ["PICKUP", "WHEAT", 2], ["PICKUP", "WHEAT", 3]],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1], ["PICKUP", "WHEAT", 2], ["PICKUP", "WHEAT", 3]],
                  ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1], ["PICKUP", "WHEAT", 2], ["PICKUP", "WHEAT", 3]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
                   ["SELL", "WHEAT", 1], ["SELL", "WHEAT", 2], ["SELL", "WHEAT", 3]]
    }

    # When the hands are in different squares
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4], "hands": [[5, 4], [4, 5]], "unlocked_quadrants": ["NW", "NE"]}, {"hires_today": 1}],
        "private": {"inventory": [{"WHEAT": 1}, {"CARROT": 1}, {}], "seed": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "WHEAT", 1], "DROP"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                  "WATER", "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "CARROT", 1], "DROP"],
                  ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

    # When the farmer is standing on a tile containing weed
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": weed_tile(2, 3, ['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": weed_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seed": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "DIG"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST", "WATER",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }
    
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
