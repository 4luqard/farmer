#!/usr/bin/env python3
import pytest
import numpy as np
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import *

def test_laziest_farmer():
    # Buys 1 wheat seed at step 1
    assert laziest_farmer({"step": 0}) == {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 1]]}

    # Doesn't do anything in a random step
    assert laziest_farmer({"step": 519}) == {"farmer": ["PASS"], "hands": [], "market": []}

    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
