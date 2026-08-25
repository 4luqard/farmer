#!/usr/bin/env python3
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import *

def test_buys_wheat_seed_on_first_step():
    """Buys 1 wheat seed at step 1"""
    assert laziest_farmer({"step": 0}) == {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}


def test_passes_on_a_later_step():
    """Doesn't do anything in a random step"""
    assert laziest_farmer({"step": 519}) == {"farmer": ["PASS"], "hands": [], "market": []}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
