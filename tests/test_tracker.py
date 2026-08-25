#!/usr/bin/env python3
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import *

def test_opponent_current_money():
    """Opponent's current coins"""
    assert _opponent_tracker({
        'player': 0,
        "farms": [{"money": 2990}, {"money": 2980}]
    }).get("money") == 2980


def test_opponent_is_player_one():
    """Opponent is player 1"""
    assert _opponent_tracker({
        'player': 1,
        "farms": [{"money": 2990}, {"money": 2980}]
    }).get("money") == 2990


def test_missing_money_key():
    """No money key or value"""
    assert _opponent_tracker({
        'player': 1,
        "farms": [{}, {"money": 2980}]
    }).get("money") == None


def test_previous_money_from_prior_step():
    """Opponent's coins in the previous step"""
    _opponent_tracker({
        'player': 0,
        "step": 13,
        "farms": [{}, {"money": 2980}]
    })
    assert _opponent_tracker({
        'player': 0,
        "step": 14,
        "farms": [{}, {"money": 2950}]
    }).get("prev_money") == 2980


def test_previous_money_at_first_step():
    """Previous coins at step 1 (No previous steps)"""
    assert _opponent_tracker({
        'player': 0,
        "step": 0,
        "farms": [{}, {"money": 2980}]
    }).get("prev_money") == 2980


def test_planted_count_empty_farm():
    """Amount of planted crops (Empty farm)"""
    assert _opponent_tracker({
        'player': 0,
        "farms": [{}, {
            "tiles": [
                [None, None, None, None, None],
                [None, None, None, None, None],
                [None, None, None, None, None],
                [None, None, None, None, None],
                [None, None, None, None, "LOCKED"]
            ]
        }]
    }).get("planted_count") == 0


def test_planted_count():
    """Amount of planted crops"""
    assert _opponent_tracker({
        'player': 0,
        "farms": [{}, {
            "tiles": [
                [{'kind': 'PLANT'}, None, None, None, None, None],
                [None, {'kind': 'PLANT'}, None, None, None, None],
                [None, None, None, None, None, None],
                [None, {'kind': 'PLANT'}, None, None, None, None],
                [None, None, None, None, "LOCKED", None],
                [None, None, None, "LOCKED", None, None]
            ]
        }]
    }).get("planted_count") == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
