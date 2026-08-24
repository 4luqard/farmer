#!/usr/bin/env python3
# Tests for _possible_actions. Each case builds an observation with obs()/farm() and
# compares the result against lists assembled from the constants below. The helpers
# return fresh lists, so no case can mutate the shared constants.
import pytest
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import *

MOVES = ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]           # always available
TEND = ["WATER", "BUILD_COOP", "BUILD_PASTURE"]              # unlocked quadrants only
PLANT_WHEAT = ["PLANT", "WHEAT"]
ONE_WHEAT = {"WHEAT": 1}
ONE_CARROT = {"CARROT": 1}

MARKET = [                                                   # offered every step
    "HIRE", "BUY_LAND",
    ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"],
    ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
    ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
    ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
]

NW_BY_SHED = [4, 4]     # the three tiles used below all touch the shed; the quadrant in
NE_BY_SHED = [5, 4]     # the name is what the unlocked_quadrants cases key off
SW_BY_SHED = [4, 5]

OPPONENT = {"hires_today": 1}   # filler: _possible_actions only ever reads farms[player]


def farm(hires=0, at=None, hands=None, unlocked=None):
    """Our farm: hands hired today, where the farmer stands, where the hands stand."""
    plot = {"hires_today": hires}
    if at is not None:
        plot["farmer"] = at
    if hands is not None:
        plot["hands"] = hands
    if unlocked is not None:
        plot["unlocked_quadrants"] = unlocked
    return plot


def obs(plot, player=0, **private):
    """One observation: our farm in the player's slot, plus private seed/shed/inventory."""
    farms = [plot, OPPONENT] if player == 0 else [OPPONENT, plot]
    return {"player": player, "farms": farms, "private": private}


def worker(*extra):          # farmer or hand on unlocked land
    return MOVES + TEND + list(extra)


def locked_worker(*extra):   # ...on a locked quadrant: it can only walk
    return MOVES + list(extra)


def market(*extra):
    return MARKET + list(extra)


def counts(verb, item, total):
    """PICKUP/SELL come one per amount: 1..total."""
    return [[verb, item, n] for n in range(1, total + 1)]


def carry(item, count):
    """What a worker holding something can do with it."""
    return [["PLACE", item, count], "DROP"]


# ---- Baseline: moves, tending, the market ----

def test_first_step_offers_moves_tending_and_the_market():
    assert _possible_actions({"step": 0}) == {
        "farmer": worker(),
        "hands": [],
        "market": market(),
    }


def test_seed_in_the_bag_adds_a_plant_action():
    assert _possible_actions(obs(farm(hires=0), seed=ONE_WHEAT)) == {
        "farmer": worker(PLANT_WHEAT),
        "hands": [],
        "market": market(),
    }


def test_hired_hand_mirrors_the_farmers_actions():
    assert _possible_actions(obs(farm(hires=1), player=1, seed=ONE_WHEAT)) == {
        "farmer": worker(PLANT_WHEAT),
        "hands": [worker(PLANT_WHEAT)],
        "market": market(),
    }


# ---- Shed-adjacent: pickups and sells ----
# NOTE: with exactly one hired hand, _possible_actions returns "hands" flat rather than
# nested (main.py:118); two or more hands come back nested. Recorded here as-is.

def test_shed_adjacent_farmer_can_pick_up_and_sell():
    assert _possible_actions(
        obs(farm(hires=1, at=NW_BY_SHED), shed=ONE_WHEAT, seed=ONE_WHEAT)
    ) == {
        "farmer": worker(PLANT_WHEAT, *counts("PICKUP", "WHEAT", 1)),
        "hands": worker(PLANT_WHEAT, *counts("PICKUP", "WHEAT", 1)),
        "market": market(*counts("SELL", "WHEAT", 1)),
    }


def test_shed_adjacent_hands_also_pick_up():
    assert _possible_actions(
        obs(farm(hires=2, at=NW_BY_SHED), shed=ONE_WHEAT, seed=ONE_WHEAT)
    ) == {
        "farmer": worker(PLANT_WHEAT, *counts("PICKUP", "WHEAT", 1)),
        "hands": [worker(PLANT_WHEAT, *counts("PICKUP", "WHEAT", 1))] * 2,
        "market": market(*counts("SELL", "WHEAT", 1)),
    }


def test_shed_adjacent_farmer_can_pick_up_and_sell_each_amount():
    assert _possible_actions(
        obs(farm(hires=2, at=NW_BY_SHED), shed={"WHEAT": 3}, seed=ONE_WHEAT)
    ) == {
        "farmer": worker(PLANT_WHEAT, *counts("PICKUP", "WHEAT", 3)),
        "hands": [worker(PLANT_WHEAT, *counts("PICKUP", "WHEAT", 3))] * 2,
        "market": market(*counts("SELL", "WHEAT", 3)),
    }


# ---- Carried inventory: place and drop ----

def test_carried_item_can_be_placed_or_dropped():
    assert _possible_actions(
        obs(farm(hires=0, at=NW_BY_SHED), inventory=[ONE_WHEAT], seed=ONE_WHEAT)
    ) == {
        "farmer": worker(PLANT_WHEAT, *carry("WHEAT", 1)),
        "hands": [],
        "market": market(),
    }


def test_farmer_and_hand_each_place_their_own_item():
    assert _possible_actions(
        obs(farm(hires=1, at=NW_BY_SHED, hands=[NE_BY_SHED]),
            inventory=[ONE_WHEAT, ONE_CARROT], seed=ONE_WHEAT)
    ) == {
        "farmer": worker(PLANT_WHEAT, *carry("WHEAT", 1)),
        "hands": worker(PLANT_WHEAT, *carry("CARROT", 1)),
        "market": market(),
    }


# ---- Locked quadrants: a worker off its unlocked land can only walk ----

def test_worker_on_a_locked_quadrant_can_only_walk():
    assert _possible_actions(
        obs(farm(hires=1, at=NW_BY_SHED, hands=[NE_BY_SHED], unlocked=["NW"]),
            inventory=[ONE_WHEAT, ONE_CARROT], seed=ONE_WHEAT)
    ) == {
        "farmer": worker(PLANT_WHEAT, *carry("WHEAT", 1)),
        "hands": locked_worker(*carry("CARROT", 1)),
        "market": market(),
    }


def test_hands_are_judged_by_their_own_tile():
    assert _possible_actions(
        obs(farm(hires=2, at=NW_BY_SHED, hands=[NE_BY_SHED, SW_BY_SHED],
                 unlocked=["NW", "NE"]),
            inventory=[ONE_WHEAT, ONE_CARROT, {}], seed=ONE_WHEAT)
    ) == {
        "farmer": worker(PLANT_WHEAT, *carry("WHEAT", 1)),
        "hands": [worker(PLANT_WHEAT, *carry("CARROT", 1)),   # NE: unlocked
                  locked_worker()],                           # SW: locked, carrying nothing
        "market": market(),
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
