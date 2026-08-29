#!/usr/bin/env python3
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import *

def farm_tiles(unlocked_quadrants):
    """Generate a 10x10 farm according to unlocked quadrants"""
    if "SE" in unlocked_quadrants:
        return [[None] * 10] * 10
    elif "SW" in unlocked_quadrants:
        return [[None] * 10] * 5 + [[None] * 5 + ["LOCKED"] * 5] * 5
    elif "NE" in unlocked_quadrants:
        return [[None] * 10] * 5 + [["LOCKED"] * 10] * 5
    else:
        return [[None] * 5 + ["LOCKED"]] * 5 + [["LOCKED"] * 10] * 5

def weed_tile(y, x, unlocked_quadrants=['NW']):
    """Place a weed at (x, y) coordinates (0 indexed coordinates)"""
    tiles = farm_tiles(unlocked_quadrants)
    tiles[y][x] = {"kind": "WEED"}
    return tiles

def plant_tile(y, x, crop="WHEAT", plntd_dy=0,
               watered=False, unwatered=1, units=0,
               lifespan=-1, fertilized=-1,
               unlocked_quadrants=['NW']):
    """Place a plant at (x, y) coordinates (0 indexed coordinates)"""
    tiles = farm_tiles(unlocked_quadrants)
    tiles[y][x] = {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": plntd_dy,
        "watered_today": watered,
        "consecutive_unwatered": unwatered,
        "yield_units": units,
        "max_lifespan_left": lifespan,
        "fertilized_until_day": fertilized
    }
    return tiles

def animal_tile(y, x, kind="COOP", animal=None, plcd_dy=0,
               fed=False, unfed=0, units=0,
               cared=False, fertilizer=False, bonus=0,
               unlocked_quadrants=['NW']):
    """Place a COOP/PASTURE at (x, y) coordinates (0 indexed coordinates)"""
    tiles = farm_tiles(unlocked_quadrants)
    tiles[y][x] = {
        "kind": kind,
        "animal": animal,
        "placed_day": plcd_dy,
        "yield_units": units,
        "fed_today": fed,
        "consecutive_unfed": unfed,
        "cared_today": cared,
        "fertilizer_available": fertilizer,
        "pending_care_bonus": bonus
    }
    return tiles

def test_first_step():
    """What actions the farmer can take in the first step"""
    assert _possible_actions({"step": 0}) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE"],
        "hands": [],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_seed_enables_plant_action():
    """When there is a seed"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 0}, {"hires_today": 1}],
        "private": {"seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"]],
        "hands": [],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_hired_hand_gets_own_actions():
    """When there is a hired hand"""
    assert _possible_actions({
        "player": 1,
        "farms": [{"hires_today": 0}, {"hires_today": 1}],
        "private": {"seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"]],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_product_in_shed():
    """When there is a product in the shed"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 1, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"shed": {"WHEAT": 1}, "seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]],
        "hands": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
                   ["SELL", "WHEAT", 1]]
    }


def test_product_in_farmer_inventory():
    """When there is a product in the inventory of a farmer"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 0, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}], "seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "WHEAT", 1], "DROP"],
        "hands": [],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_product_in_farmer_and_hand_inventory():
    """When there is a product in the inventory of a farmer and hand"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 1, "farmer": [4, 4], "hands": [[5, 4]]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}], "seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "WHEAT", 1], "DROP"],
        "hands": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "CARROT", 1], "DROP"],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_unit_in_locked_area():
    """When the farmer or the hand is in a locked area"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 1, "farmer": [4, 4], "hands": [[5, 4]], "unlocked_quadrants": ["NW"]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}], "seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "WHEAT", 1], "DROP"],
        "hands": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   ["PLACE", "CARROT", 1], "DROP"],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_multiple_hires():
    """When there are more than 1 hires"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"shed": {"WHEAT": 1}, "seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]],
                  ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
                   ["SELL", "WHEAT", 1]]
    }


def test_multiple_item_counts():
    """When there are more than one item"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"shed": {"WHEAT": 3}, "seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1], ["PICKUP", "WHEAT", 2], ["PICKUP", "WHEAT", 3]],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1], ["PICKUP", "WHEAT", 2], ["PICKUP", "WHEAT", 3]],
                  ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "WHEAT", 1], ["PICKUP", "WHEAT", 2], ["PICKUP", "WHEAT", 3]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
                   ["SELL", "WHEAT", 1], ["SELL", "WHEAT", 2], ["SELL", "WHEAT", 3]]
    }


def test_hands_in_different_squares():
    """When the hands are in different squares"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4], "hands": [[5, 4], [4, 5]], "unlocked_quadrants": ["NW", "NE"]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}, {}], "seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "WHEAT", 1], "DROP"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                  "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PLACE", "CARROT", 1], "DROP"],
                  ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_farmer_on_weed_tile():
    """When the farmer is standing on a tile containing weed"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": weed_tile(2, 3, ['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": weed_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "DIG"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_farmer_on_plant_tile():
    """When the farmer is standing on a tile containing a given plant"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": plant_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": plant_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "WATER", "DIG"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_farmer_on_plant_tile_with_fertilizer():
    """When the farmer is standing on a tile containing a given plant and has fertilizer"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": plant_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": plant_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"FERTILIZER": 1}, {}], "seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "WATER", "DIG", "FERTILIZE"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

    
def test_farmer_on_harvestable_plant_tile():
    """When the farmer is standing on a tile containing a given harvestable plant"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": plant_tile(2, 3, units=1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": plant_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "WATER", "DIG", "HARVEST"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

def test_farmer_on_watered_plant_tile():
    """When the farmer is standing on a tile containing a watered plant"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": plant_tile(2, 3, watered=True), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": plant_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "DIG"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }

    
def test_farmer_on_fertilized_plant_tile():
    """When the farmer is standing on a tile containing a fertilized plant"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": plant_tile(2, 3, fertilized=3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": plant_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"FERTILIZER": 1}, {}], "seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "WATER", "DIG"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_animal_in_shed():
    """When there is an animal in the shed"""
    assert _possible_actions({
        "player": 0,
        "farms": [{"hires_today": 1, "farmer": [4, 4]}, {"hires_today": 1}],
        "private": {"shed": {"GOOSE": 1}, "seeds": {"WHEAT": 1}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "GOOSE", 1]],
        "hands": ["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "WHEAT"],
                   ["PICKUP", "GOOSE", 1]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }


def test_farmer_on_a_coop_tile():
    """When the farmer is standing on a tile containing a coop"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": animal_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": animal_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"COW": 1}, {}], "seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "DIG"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }   


def test_farmer_on_a_coop_tile_with_a_goose():
    """When the farmer is standing on a tile containing a coop with a goose"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": animal_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": animal_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"GOOSE": 1}, {}], "seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "DIG", ["PLACE", "GOOSE", 1]],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }   


def test_farmer_on_a_coop_tile_with_a_goose_and_wheat():
    """When the farmer is standing on a tile containing a animal with wheat"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": animal_tile(2, 3, animal="GOOSE", fed=False, unfed=1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": animal_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"WHEAT": 10}, {}], "seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "CARE", "FEED"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }   


def test_farmer_on_a_coop_tile_with_a_goose_egg():
    """When the farmer is standing on a tile containing a goose tile with harvestable egg"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": animal_tile(2, 3, animal="GOOSE", fed=False, unfed=1, units=1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": animal_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"WHEAT": 10}, {}], "seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "CARE", "FEED", "HARVEST"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }   


def test_farmer_on_a_pasture_tile():
    """When the farmer is standing on a tile containing a pasture"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": animal_tile(2, 3, kind="PASTURE"), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": animal_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"COW": 10}, {}], "seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "DIG", ["PLACE", "COW", 1]],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }   


def test_farmer_on_a_pasture_tile_with_fertilizer():
    """When the farmer is standing on a tile containing animal with fertilizer"""
    assert _possible_actions({
        "player": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": animal_tile(2, 3, animal="GOOSE", fertilizer=True), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": animal_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"COW": 10}, {}], "seeds": {"CARROT": 2}}
    }) == {
        "farmer": ["PASS", "NORTH", "SOUTH", "EAST", "WEST", "CARE", "COLLECT_FERTILIZER"],
        "hands": [["PASS", "NORTH", "SOUTH", "EAST", "WEST",
                   "BUILD_COOP", "BUILD_PASTURE", ["PLANT", "CARROT"]]],
        "market": ["HIRE", "BUY_LAND",
                   ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"], ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
                   ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
                   ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"]]
    }   

  
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
