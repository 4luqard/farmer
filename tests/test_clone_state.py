#!/usr/bin/env python3
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import _clone_state


def test_cloned_is_same_as_the_original():
    original_state = {
        "player": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4], "hands": [[5, 4], [4, 5]], "unlocked_quadrants": ["NW", "NE"]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}, {}], "seeds": {"WHEAT": 1}}
    }
    cloned_state = _clone_state(original_state)
    assert original_state == cloned_state

    
def test_cloned_is_independent_of_the_original():
    original_state = {
        "player": 0,
        "day": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4], "hands": [[5, 4], [4, 5]], "unlocked_quadrants": ["NW", "NE"]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}, {}], "seeds": {"WHEAT": 1}}
    }
    cloned_state = _clone_state(original_state)
    cloned_state['day'] = "modified"
    assert original_state != "modified"

    
def test_cloned_is_not_shallow():
    original_state = {
        "player": 0,
        "day": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4], "hands": [[5, 4], [4, 5]], "unlocked_quadrants": ["NW", "NE"]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}, {}], "seeds": {"WHEAT": 1}}
    }
    cloned_state = _clone_state(original_state)
    cloned_state['farms'][0]['hires_today'] = "modified"
    cloned_state['farms'][0]['farmer'][0] = "modified"
    assert original_state['farms'][0]['hires_today'] != "modified"
    assert original_state['farms'][0]['farmer'][0] != "modified"

    
def test_cloned_is_different_object():
    original_state = {
        "player": 0,
        "day": 0,
        "farms": [{"hires_today": 2, "farmer": [4, 4], "hands": [[5, 4], [4, 5]], "unlocked_quadrants": ["NW", "NE"]}, {"hires_today": 1}],
        "private": {"inventories": [{"WHEAT": 1}, {"CARROT": 1}, {}], "seeds": {"WHEAT": 1}}
    }
    cloned_state = _clone_state(original_state)
    assert cloned_state is not original_state
    assert cloned_state['farms'][0]['unlocked_quadrants'] is not original_state['farms'][0]['unlocked_quadrants']

    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
