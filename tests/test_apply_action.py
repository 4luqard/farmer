#!/usr/bin/env python3
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import _apply_action


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
    
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
