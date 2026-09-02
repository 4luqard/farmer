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


def _animal_tile(y, x, kind="COOP", animal=None, plcd_dy=0,
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


def test_pass_action():
    original_state = {
        "player": 0,
        "day": 0,
        "hour": 0,
        "farms": [{"farmer": [4, 4], "hands": [], "unlocked_quadrants": ["NW", "NE"]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}, {}], "seeds": {"WHEAT": 1}}
    }
    action_dict = {
        'farmer': ["PASS"],
        'hands': [],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['day'] == 0
    assert _apply_action(original_state, action_dict)['hour'] == 1

    after_action_state = original_state.copy()
    after_action_state['hour'] = 1
    assert _apply_action(original_state, action_dict) == after_action_state

    
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
            {'hires_today': 1, "farmer": [4, 4], "hands": [[5, 4]], "tiles": _plant_tile(2, 3, ['NW', 'NE']), "unlocked_quadrants": ['NW', 'NE']}
        ],
        "private": {"seeds": {"CARROT": 2}}
    }
    action_dict = {
        'farmer': ['WATER'],
        'hands': [['PASS']],
        'market': []
    }
    assert _apply_action(original_state, action_dict)['farms'][0]['tiles'][2][3]['watered_today'] == True

    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
