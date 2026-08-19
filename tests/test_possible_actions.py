#!/usr/bin/env python3
"""Tests for `_possible_actions`.

Each case builds one observation with `obs(...)` and compares the whole action
dict against `expect(...)`. The constants and helpers below name the pieces that
repeat, so a case shows only what makes it different.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import *

# ---- The pieces every action list is built from ----

MOVES = ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]   # legal on any tile
TENDING = ["WATER", "BUILD_COOP", "BUILD_PASTURE"]   # only on an unlocked tile
PLANT_WHEAT = ["PLANT", "WHEAT"]                     # unlocked tile + a wheat seed in stock

ON_LOCKED_TILE = MOVES
ON_UNLOCKED_TILE = MOVES + TENDING + [PLANT_WHEAT]

MARKET = [
    "HIRE", "BUY_LAND",
    ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"],
    ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
    ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
    ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
]

WHEAT_SEED = {"WHEAT": 1}

AT_SHED = [4, 4]        # NW quadrant, and one of the four tiles touching the shed
EAST_OF_SHED = [5, 4]   # NE quadrant
SOUTH_OF_SHED = [4, 5]  # SW quadrant

OTHER_FARM = {"hires_today": 0}  # the opponent's farm; kept free of hires so a case
                                 # that read the wrong `player` index would fail


# ---- Building an observation and the dict it should produce ----

def obs(*, player=0, hires=0, farmer=None, hands=None, unlocked=None,
        seed=WHEAT_SEED, shed=None, inventory=None):
    """An observation whose farm at index `player` is the one described here.

    Only the keys a case cares about are set, so the call site reads as the
    scenario under test.
    """
    farm = {"hires_today": hires}
    if farmer is not None:
        farm["farmer"] = farmer
    if hands is not None:
        farm["hands"] = hands
    if unlocked is not None:
        farm["unlocked_quadrants"] = unlocked

    private = {"seed": seed}
    if shed is not None:
        private["shed"] = shed
    if inventory is not None:
        private["inventory"] = inventory

    farms = [OTHER_FARM, OTHER_FARM]
    farms[player] = farm
    return {"player": player, "farms": farms, "private": private}


def expect(farmer, hands=None, market=None):
    """The full dict `_possible_actions` returns; hands and market default to the quiet case."""
    return {
        "farmer": farmer,
        "hands": [] if hands is None else hands,
        "market": MARKET if market is None else market,
    }


def pickup(item, *counts):
    """One PICKUP per amount that can be taken out of the shed."""
    return [["PICKUP", item, n] for n in counts]


def sell(item, *counts):
    """One SELL per amount that can be taken out of the shed."""
    return [["SELL", item, n] for n in counts]


def carrying(item, count):
    """What a worker already holding `count` of `item` may do with it."""
    return [["PLACE", item, count], "DROP"]


# ---- Cases ----

def test_an_empty_observation_offers_movement_farm_work_and_the_market():
    assert _possible_actions({"step": 0}) == expect(farmer=MOVES + TENDING)


def test_a_seed_in_stock_adds_a_plant_action():
    assert _possible_actions(obs()) == expect(farmer=ON_UNLOCKED_TILE)


def test_the_players_own_farm_decides_how_many_hands_there_are():
    assert _possible_actions(obs(player=1, hires=1)) == expect(
        farmer=ON_UNLOCKED_TILE,
        hands=[ON_UNLOCKED_TILE],
    )


def test_next_to_the_shed_the_stock_can_be_picked_up_and_sold():
    both = ON_UNLOCKED_TILE + pickup("WHEAT", 1)
    assert _possible_actions(obs(hires=1, farmer=AT_SHED, shed={"WHEAT": 1})) == expect(
        farmer=both,
        hands=both,  # a single hire beside the shed: one flat list, not a list of lists
        market=MARKET + sell("WHEAT", 1),
    )


def test_a_carried_item_can_be_placed_or_dropped():
    assert _possible_actions(obs(farmer=AT_SHED, inventory=[{"WHEAT": 1}])) == expect(
        farmer=ON_UNLOCKED_TILE + carrying("WHEAT", 1),
    )


def test_each_worker_places_only_what_it_is_carrying():
    assert _possible_actions(obs(
        hires=1, farmer=AT_SHED, hands=[EAST_OF_SHED],
        inventory=[{"WHEAT": 1}, {"CARROT": 1}],
    )) == expect(
        farmer=ON_UNLOCKED_TILE + carrying("WHEAT", 1),
        hands=ON_UNLOCKED_TILE + carrying("CARROT", 1),
    )


def test_a_locked_quadrant_leaves_a_worker_only_movement():
    assert _possible_actions(obs(
        hires=1, farmer=AT_SHED, hands=[EAST_OF_SHED], unlocked=["NW"],
        inventory=[{"WHEAT": 1}, {"CARROT": 1}],
    )) == expect(
        farmer=ON_UNLOCKED_TILE + carrying("WHEAT", 1),
        hands=ON_LOCKED_TILE + carrying("CARROT", 1),
    )


def test_every_hire_gets_the_shed_actions():
    hand = ON_UNLOCKED_TILE + pickup("WHEAT", 1)
    assert _possible_actions(obs(hires=2, farmer=AT_SHED, shed={"WHEAT": 1})) == expect(
        farmer=hand,
        hands=[hand, hand],  # more than one hire: a list per hand
        market=MARKET + sell("WHEAT", 1),
    )


def test_a_stack_in_the_shed_offers_every_amount():
    hand = ON_UNLOCKED_TILE + pickup("WHEAT", 1, 2, 3)
    assert _possible_actions(obs(hires=2, farmer=AT_SHED, shed={"WHEAT": 3})) == expect(
        farmer=hand,
        hands=[hand, hand],
        market=MARKET + sell("WHEAT", 1, 2, 3),
    )


def test_hands_in_different_quadrants_get_different_actions():
    assert _possible_actions(obs(
        hires=2, farmer=AT_SHED, hands=[EAST_OF_SHED, SOUTH_OF_SHED],
        unlocked=["NW", "NE"],
        inventory=[{"WHEAT": 1}, {"CARROT": 1}, {}],
    )) == expect(
        farmer=ON_UNLOCKED_TILE + carrying("WHEAT", 1),
        hands=[
            ON_UNLOCKED_TILE + carrying("CARROT", 1),  # NE: unlocked, carrying a carrot
            ON_LOCKED_TILE,                            # SW: locked, empty-handed
        ],
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
