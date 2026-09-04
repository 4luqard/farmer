#!/usr/bin/env python3
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import _get_reward


def test_player1_wins():
    state = {
        "player": 0,
        "day": 30,
        "hour": 0,
        "farms": [{"money": 5235}, {"money": 3873}]
    }
    assert _get_reward(state) == (state['farms'][0]['money'] - state['farms'][1]['money'])

    
def test_player2_wins():
    state = {
        "player": 0,
        "day": 30,
        "hour": 0,
        "farms": [{"money": 5235}, {"money": 7426}]
    }
    assert _get_reward(state) == (state['farms'][0]['money'] - state['farms'][1]['money'])

    
def test_draw():
    state = {
        "player": 0,
        "day": 30,
        "hour": 0,
        "farms": [{"money": 3000}, {"money": 3000}]
    }
    assert _get_reward(state) == (state['farms'][0]['money'] - state['farms'][1]['money'])
   
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
