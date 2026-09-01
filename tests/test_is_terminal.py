#!/usr/bin/env python3
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import _is_terminal


def test_player1_wins():
    state = {
        "player": 0,
        "day": 30,
        "hour": 0,
        "farms": [{"money": 5235}, {"money": 3873}]
    }
    assert _is_terminal(state)

    
def test_player2_wins():
    state = {
        "player": 0,
        "day": 30,
        "hour": 0,
        "farms": [{"money": 5235}, {"money": 7426}]
    }
    assert _is_terminal(state)

    
def test_draw():
    state = {
        "player": 0,
        "day": 30,
        "hour": 0,
        "farms": [{"money": 3000}, {"money": 3000}]
    }
    assert _is_terminal(state)

    
def test_ongoing_game_last_step():
    state = {
        "player": 0,
        "day": 29,
        "hour": 23,
        "farms": [{"money": 2344}, {"money": 5346}]
    }
    assert not _is_terminal(state)

    
def test_ongoing_game_random_step():
    state = {
        "player": 0,
        "day": 23,
        "hour": 21,
        "farms": [{"money": 23443}, {"money": 5346}]
    }
    assert not _is_terminal(state)
    
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
