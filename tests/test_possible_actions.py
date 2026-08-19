#!/usr/bin/env python3
"""Tests for _possible_actions: the actions the farmer, each hired hand and the
market offer for one observation. The helpers below spell out the action
vocabulary and build observations, so every case shows only the one condition it
is about.
"""
import os
import sys

import pytest

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from main import _possible_actions

# ---- Action vocabulary ----
# Single actions are passed to worker()/market() as they are; helpers that stand
# for a run of actions return a list and are splatted: worker(*pickups(...)).

MOVE = ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]
TEND = ["WATER", "BUILD_COOP", "BUILD_PASTURE"]
BUY = [
    "HIRE", "BUY_LAND",
    ["BUY_SEED", "WHEAT"], ["BUY_SEED", "CARROT"], ["BUY_SEED", "TOMATO"],
    ["BUY_SEED", "STRAWBERRY"], ["BUY_SEED", "MELON"],
    ["BUY_PRODUCT", "WHEAT"], ["BUY_PRODUCT", "FERTILIZER"],
    ["BUY_ANIMAL", "GOOSE"], ["BUY_ANIMAL", "COW"], ["BUY_ANIMAL", "SHEEP"],
]


def worker(*extra, locked=False):
    """One worker's actions: moves, tending on an unlocked tile, then extra."""
    return [*MOVE, *([] if locked else TEND), *extra]


def market(*extra):
    """The market's actions: the fixed buy list, then extra."""
    return [*BUY, *extra]


def plant(crop):
    """Sowing a crop the player holds seed for."""
    return ["PLANT", crop]


def pickups(item, count):
    """Taking 1..count of an item out of the shed."""
    return [["PICKUP", item, n] for n in range(1, count + 1)]


def sells(item, count):
    """Selling 1..count of an item out of the shed."""
    return [["SELL", item, n] for n in range(1, count + 1)]


def unload(item, count):
    """Putting a carried item into the shed, then dropping what is left."""
    return [["PLACE", item, count], "DROP"]


# ---- Observations ----
# The four tiles around the shed, named by the quadrant they sit in: a worker
# beside the shed can reach it, and its quadrant decides whether it is unlocked.

SHED_NW, SHED_NE, SHED_SW = [4, 4], [5, 4], [4, 5]

OPPONENT = {"hires_today": 1}  # the other player's farm, which is never read


def obs(player=0, *, hires=0, farmer=None, hands=None, unlocked=None,
        seed=None, shed=None, inventory=None):
    """An observation holding the player's farm at farms[player] and an opponent
    farm at the other index. Keys a case does not set stay out of the payload."""
    farm = {"hires_today": hires}
    farm.update({key: value for key, value in (
        ("farmer", farmer), ("hands", hands), ("unlocked_quadrants", unlocked),
    ) if value is not None})
    private = {key: value for key, value in (
        ("seed", seed), ("shed", shed), ("inventory", inventory),
    ) if value is not None}
    farms = [OPPONENT, OPPONENT]
    farms[player] = farm
    return {"player": player, "farms": farms, "private": private}


# 1. bare first step: no farm at all, so every default applies
def test_first_step_offers_the_base_actions():
    assert _possible_actions({"step": 0}) == {
        "farmer": worker(),
        "hands": [],
        "market": market(),
    }


# 2. seed in store: planting joins the farmer's actions
def test_seed_in_store_adds_planting():
    assert _possible_actions(obs(seed={"WHEAT": 1})) == {
        "farmer": worker(plant("WHEAT")),
        "hands": [],
        "market": market(),
    }


# 3. one hire, away from the shed: the hand mirrors the farmer, and farms[1] is
#    the farm read when the player is 1
def test_a_hire_away_from_the_shed_mirrors_the_farmer():
    assert _possible_actions(obs(player=1, hires=1, seed={"WHEAT": 1})) == {
        "farmer": worker(plant("WHEAT")),
        "hands": [worker(plant("WHEAT"))],
        "market": market(),
    }


# 4. beside the shed: its stock can be picked up, and the market can sell it.
#    A single hand's actions come back flat here, not wrapped in a list.
def test_beside_the_shed_stock_can_be_picked_up_and_sold():
    beside_the_shed = worker(plant("WHEAT"), *pickups("WHEAT", 1))
    assert _possible_actions(obs(
        hires=1, farmer=SHED_NW, seed={"WHEAT": 1}, shed={"WHEAT": 1},
    )) == {
        "farmer": beside_the_shed,
        "hands": beside_the_shed,
        "market": market(*sells("WHEAT", 1)),
    }


# 5. carrying an item beside the shed: it can be placed, and the rest dropped
def test_a_carried_item_can_be_placed_in_the_shed():
    assert _possible_actions(obs(
        farmer=SHED_NW, seed={"WHEAT": 1}, inventory=[{"WHEAT": 1}],
    )) == {
        "farmer": worker(plant("WHEAT"), *unload("WHEAT", 1)),
        "hands": [],
        "market": market(),
    }


# 6. the inventory list is per worker: entry 0 is the farmer's, entry 1 the hand's
def test_farmer_and_hand_place_their_own_inventories():
    assert _possible_actions(obs(
        hires=1, farmer=SHED_NW, hands=[SHED_NE],
        seed={"WHEAT": 1}, inventory=[{"WHEAT": 1}, {"CARROT": 1}],
    )) == {
        "farmer": worker(plant("WHEAT"), *unload("WHEAT", 1)),
        "hands": worker(plant("WHEAT"), *unload("CARROT", 1)),
        "market": market(),
    }


# 7. a locked tile: the hand in NE keeps only its moves and its inventory
def test_a_locked_tile_leaves_only_moves_and_inventory():
    assert _possible_actions(obs(
        hires=1, farmer=SHED_NW, hands=[SHED_NE], unlocked=["NW"],
        seed={"WHEAT": 1}, inventory=[{"WHEAT": 1}, {"CARROT": 1}],
    )) == {
        "farmer": worker(plant("WHEAT"), *unload("WHEAT", 1)),
        "hands": worker(*unload("CARROT", 1), locked=True),
        "market": market(),
    }


# 8. two hires: each one gets its own list
def test_two_hires_each_get_a_list():
    beside_the_shed = worker(plant("WHEAT"), *pickups("WHEAT", 1))
    assert _possible_actions(obs(
        hires=2, farmer=SHED_NW, seed={"WHEAT": 1}, shed={"WHEAT": 1},
    )) == {
        "farmer": beside_the_shed,
        "hands": [beside_the_shed, beside_the_shed],
        "market": market(*sells("WHEAT", 1)),
    }


# 9. a stack in the shed: one pickup and one sell action per amount
def test_a_stack_offers_one_action_per_amount():
    beside_the_shed = worker(plant("WHEAT"), *pickups("WHEAT", 3))
    assert _possible_actions(obs(
        hires=2, farmer=SHED_NW, seed={"WHEAT": 1}, shed={"WHEAT": 3},
    )) == {
        "farmer": beside_the_shed,
        "hands": [beside_the_shed, beside_the_shed],
        "market": market(*sells("WHEAT", 3)),
    }


# 10. hands on different tiles: each is judged by the tile it stands on, and the
#     one carrying nothing has nothing to place
def test_each_hand_is_judged_by_its_own_tile():
    assert _possible_actions(obs(
        hires=2, farmer=SHED_NW, hands=[SHED_NE, SHED_SW], unlocked=["NW", "NE"],
        seed={"WHEAT": 1}, inventory=[{"WHEAT": 1}, {"CARROT": 1}, {}],
    )) == {
        "farmer": worker(plant("WHEAT"), *unload("WHEAT", 1)),
        "hands": [
            worker(plant("WHEAT"), *unload("CARROT", 1)),
            worker(locked=True),
        ],
        "market": market(),
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
