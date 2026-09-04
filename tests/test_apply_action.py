#!/usr/bin/env python3
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import _apply_action


def _farm_tiles(unlocked_quadrants):
    """Generate a 10x10 farm according to unlocked quadrants"""
    if "SE" in unlocked_quadrants:
        return [[None] * 10] * 10
    elif "SW" in unlocked_quadrants:
        return [[None] * 10] * 5 + [[None] * 5 + ["LOCKED"] * 5] * 5
    elif "NE" in unlocked_quadrants:
        return [[None] * 10] * 5 + [["LOCKED"] * 10] * 5
    else:
        return [[None] * 5 + ["LOCKED"] * 5] * 5 + [["LOCKED"] * 10] * 5

    
def _weed_tile(y, x, unlocked_quadrants=['NW']):
    """Place a weed at (x, y) coordinates (0 indexed coordinates)"""
    tiles = _farm_tiles(unlocked_quadrants)
    tiles[y][x] = {"kind": "WEED"}
    return tiles


def _plant_tile(y, x, crop="WHEAT", plntd_dy=0,
               watered=False, unwatered=1, units=0,
               lifespan=5, fertilized=-1,
               unlocked_quadrants=['NW']):
    """Place a plant at (x, y) coordinates (0 indexed coordinates)"""
    tiles = _farm_tiles(unlocked_quadrants)
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


def _animal_tile(y, x, kind="COOP", animal=None, plcd_dy=-1,
               fed=False, unfed=0, units=0,
               cared=False, fertilizer=False, bonus=0,
               unlocked_quadrants=['NW']):
    """Place a COOP/PASTURE at (x, y) coordinates (0 indexed coordinates)"""
    tiles = _farm_tiles(unlocked_quadrants)
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


def _market():
    """Prices and inventory of each thing in the market"""
    prices = {
        "WHEAT": 25,
        "CARROT": 35,
        "TOMATO": 60,
        "STRAWBERRY": 120,
        "MELON": 250,
        "EGG": 50,
        "MILK": 160,
        "WOOL": 200,
        "FERTILIZER": 100
    }
    inventory = {
        "WHEAT": 10000,
        "CARROT": 10000,
        "TOMATO": 10000,
        "STRAWBERRY": 10000,
        "MELON": 10000,
        "EGG": 10000,
        "MILK": 10000,
        "WOOL": 10000,
        "FERTILIZER": 10000
    }
    return {"inventory": inventory, "prices": prices}

    
def test_movement_actions():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 23,
        "farms": [{"hires_today": 2, "farmer": [4, 4], "hands": [[5, 4], [4, 5]], "unlocked_quadrants": ["NW", "NE"]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}, {}], "seeds": {"WHEAT": 1}}
    }
    movement_actions = ['NORTH', 'SOUTH', 'WEST', 'EAST']
    farmer_positions = [[4, 3], [4, 5], [3, 4], [5, 4]]
    hands_positions = [
        [[5, 3], [4, 4]],
        [[5, 5], [4, 6]],
        [[4, 4], [3, 5]],
        [[6, 4], [5, 5]]
    ]
    for i in range(4):
        action_dict = {
            'farmer': [movement_actions[i]],
            'hands': [[movement_actions[i]], [movement_actions[i]]],
            'market': []
        }
        assert _apply_action(original_state, action_dict)['day'] == 1
        assert _apply_action(original_state, action_dict)['hour'] == 0
        assert _apply_action(original_state, action_dict)['farms'][0]['farmer'] == farmer_positions[i]
        assert _apply_action(original_state, action_dict)['farms'][0]['hands'] == hands_positions[i]

        
def test_water():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _plant_tile(2, 3, watered=False), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['WATER'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'][2][3]['watered_today'] == True

    
def test_harvest_plant():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _plant_tile(2, 3, units=2), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['HARVEST'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'][2][3] == None

    
def test_harvest_ongoing_plant():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _plant_tile(2, 3, crop='TOMATO', units=2, lifespan=-1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['HARVEST'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _plant_tile(2, 3, crop='TOMATO', units=0, lifespan=-1)

    
def test_harvest_animal():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _animal_tile(2, 3, animal="GOOSE", units=1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['HARVEST'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _animal_tile(2, 3, animal="GOOSE")

    
def test_fertilize():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _plant_tile(2, 3, fertilized=-1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['FERTILIZE'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _plant_tile(2, 3, fertilized=3)

    
def test_dig_weed():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _weed_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _weed_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['DIG'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'][2][3] == None

    
def test_dig_plant():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _plant_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['DIG'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'][2][3] == None

    
def test_dig_empty_coop_pasture():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _animal_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['DIG'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'][2][3] == None


def test_drop():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _animal_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"CARROT": 3, "GOOSE": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['DROP'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['private']['shed'] == {"CARROT": 3, "GOOSE": 2}
    assert _apply_action(original_state, action_dict)['private']['inventories'] == [{}, {}]


def test_drop_shed_overflow():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _animal_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"shed": {"CARROT": 96}, "inventories": [{"CARROT": 3, "GOOSE": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['DROP'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['private']['shed'] == {"CARROT": 99, "GOOSE": 1}
    assert _apply_action(original_state, action_dict)['private']['inventories'] == [{}, {}]

    
def test_build_coop():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['BUILD_COOP'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _animal_tile(2, 3)

    
def test_build_pasture():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['BUILD_PASTURE'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _animal_tile(2, 3, kind="PASTURE")

    
def test_feed():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 23,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"WHEAT": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['FEED'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict, weeds_enabled=False)['farms'][0]['tiles'] == _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=0, fertilizer=True)
    assert _apply_action(original_state, action_dict, weeds_enabled=False)['private']['inventories'][0] == {"WHEAT": 1}

    
def test_collect_fertilizer():
    original_state = {
        "player": 0,
        "day": 2,
        "hour": 0,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=1, fertilizer=True), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['COLLECT_FERTILIZER'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=1, fertilizer=False)
    assert _apply_action(original_state, action_dict)['private']['inventories'][0] == {"FERTILIZER": 1}

    
def test_care():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 23,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _animal_tile(2, 3, animal="GOOSE", fed=True, unfed=0, cared=False), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"WHEAT": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['CARE'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict, weeds_enabled=False)['farms'][0]['tiles'] == _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=0, bonus=1, fertilizer=True)

    
def test_care_unfed():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 23,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=0, cared=False), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"WHEAT": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['CARE'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict, weeds_enabled=False)['farms'][0]['tiles'] == _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=1, bonus=0, fertilizer=True)

    
def test_plant_any_crop():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"WHEAT": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': [["PLANT", "CARROT"]],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _plant_tile(2, 3, crop="CARROT", lifespan=4)
    assert _apply_action(original_state, action_dict)['private']['seeds']['CARROT'] == 1

    
def test_pickup():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': [["PICKUP", "GOOSE", 2]],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['private']['inventories'][0] == {"WHEAT": 2, "GOOSE": 2}
    assert _apply_action(original_state, action_dict)['private']['shed']['GOOSE'] == 1

    
def test_place_on_coop_and_shed():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _animal_tile(4, 4), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': [["PLACE", "GOOSE", 1]],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['private']['inventories'][0] == {"WHEAT": 2}
    assert _apply_action(original_state, action_dict)['private']['shed']['GOOSE'] == 3
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _animal_tile(4, 4, animal="GOOSE")

    
def test_place_on_shed():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _animal_tile(2, 3), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': [["PLACE", "GOOSE", 1]],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['private']['inventories'][0] == {"WHEAT": 2}
    assert _apply_action(original_state, action_dict)['private']['shed']['GOOSE'] == 4

    
def test_multiple_action_at_the_same_time():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': [["PLACE", "GOOSE", 1]],
        'hands': [['PLANT', 'CARROT']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['private']['inventories'][0] == {"WHEAT": 2}
    assert _apply_action(original_state, action_dict)['private']['shed']['GOOSE'] == 4
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _plant_tile(4, 1, crop="CARROT", lifespan=4)
    assert _apply_action(original_state, action_dict)['private']['seeds']['CARROT'] == 1

    
def test_multiple_same_action_at_the_same_time():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': [["PLANT", "CARROT"]],
        'hands': [['PLANT', 'CARROT']],
        'market': []
    }
    after_actions_farm_tiles = _plant_tile(4, 4, crop="CARROT", lifespan=4)
    after_actions_farm_tiles[4][1] = {
        "kind": "PLANT",
        "crop": "CARROT",
        "planted_day": 0,
        "watered_today": False,
        "consecutive_unwatered": 1,
        "yield_units": 0,
        "max_lifespan_left": 4,
        "fertilized_until_day": -1
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == after_actions_farm_tiles
    assert _apply_action(original_state, action_dict)['private']['seeds']['CARROT'] == 0

    
def test_multiple_same_action_at_the_same_time_without_enough_resources():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': [["PLANT", "CARROT"]],
        'hands': [['PLANT', 'CARROT']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _farm_tiles(['NW'])
    assert _apply_action(original_state, action_dict)['private']['seeds']['CARROT'] == 1

    
def test_hire():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': [["HIRE"]]
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['hires_today'] == 2
    assert _apply_action(original_state, action_dict)['farms'][0]['hands'][1] == [5, 4]
    assert _apply_action(original_state, action_dict)['farms'][0]['money'] == 2699

    
def test_buy_land():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': [["BUY_LAND"]]
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _farm_tiles(['NW', 'NE'])
    assert _apply_action(original_state, action_dict)['farms'][0]['money'] == 1700

    
def test_buy_seed():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': [["BUY_SEED", "CARROT", 1]]
    }
    assert _apply_action(original_state, action_dict)['private']['seeds']['CARROT'] == 2
    assert _apply_action(original_state, action_dict)['farms'][0]['money'] == 2680

    
def test_buy_product():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "market": _market(),
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': [["BUY_PRODUCT", "WHEAT", 1]]
    }
    assert _apply_action(original_state, action_dict)['private']['shed']['WHEAT'] == 1
    assert _apply_action(original_state, action_dict)['farms'][0]['money'] == 2674

    
def test_buy_animal():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {'shed': {"GOOSE": 3}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': [["BUY_ANIMAL", "GOOSE", 1]]
    }
    assert _apply_action(original_state, action_dict)['private']['shed']['GOOSE'] == 4
    assert _apply_action(original_state, action_dict)['farms'][0]['money'] == 2400


def test_sell():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "market": _market(),
        "private": {'shed': {"WHEAT": 4}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': [["SELL", "WHEAT", 1]]
    }
    assert _apply_action(original_state, action_dict)['private']['shed']['WHEAT'] == 3
    assert _apply_action(original_state, action_dict)['farms'][0]['money'] == 2725

        
def test_plant_turning_to_weed_by_not_watering():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 23,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _plant_tile(2, 3, watered=False, unwatered=1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict, weeds_enabled=False)['farms'][0]['tiles'] == _weed_tile(2, 3)


def test_animal_escaping():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 23,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"WHEAT": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['PASS'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict, weeds_enabled=False)['farms'][0]['tiles'] == _animal_tile(2, 3)
    assert _apply_action(original_state, action_dict, weeds_enabled=False)['private']['inventories'][0] == {"WHEAT": 2}


def test_order_count_truncation():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 3,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "market": _market(),
        "private": {'shed': {"WHEAT": 4}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': [["BUY_PRODUCT", "WHEAT", 1]] * 12
    }
    assert _apply_action(original_state, action_dict)['private']['shed']['WHEAT'] == 14


def test_town_consumption():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 0,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "market": _market(),
        "private": {'shed': {"WHEAT": 4}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['market']['inventory'] == {
        "WHEAT": 9999,
        "CARROT": 9999,
        "TOMATO": 9999,
        "STRAWBERRY": 9999,
        "MELON": 9999,
        "EGG": 9999,
        "MILK": 9999,
        "WOOL": 9999,
        "FERTILIZER": 10000
    }


def test_town_shop_consumption():
    original_state = {
        "player": 0,
        "day": 4,
        "hour": 1,
        "farms": [
            {"money": 2700, "hires_today": 1, "farmer": [4, 4], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "market": _market(),
        "town": {
            "unlocked_shops": ["BAKERY"]
        },
        "private": {'shed': {"WHEAT": 4}, "inventories": [{"WHEAT": 2, "GOOSE": 1}, {}], "seeds": {"CARROT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [["PASS"]],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['market']['inventory'] == {
        "WHEAT": 9999,
        "CARROT": 10000,
        "TOMATO": 10000,
        "STRAWBERRY": 10000,
        "MELON": 10000,
        "EGG": 9999,
        "MILK": 10000,
        "WOOL": 10000,
        "FERTILIZER": 10000
    }


def test_plant_turning_to_weed_by_decay():
    original_state = {
        "player": 0,
        "day": 6,
        "hour": 5,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _plant_tile(2, 3, units=1, watered=False, unwatered=1), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'] == _weed_tile(2, 3)


def test_fertilizer_appearing():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 23,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=0), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _animal_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"inventories": [{"WHEAT": 2}, {}], "seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['PASS'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict, weeds_enabled=False)['farms'][0]['tiles'] == _animal_tile(2, 3, animal="GOOSE", fed=False, unfed=1, fertilizer=True)


def test_random_weed_spawn_chance():
    original_state = {
        "player": 0,
        "day": 1,
        "hour": 23,
        "farms": [
            {"hires_today": 1, "farmer": [3, 2], "hands": [[1, 4]], "tiles": _farm_tiles(['NW']), "unlocked_quadrants": ['NW']},
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, unlocked_quadrants=['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict, seed=156)['farms'][0]['tiles'] == _weed_tile(1, 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
