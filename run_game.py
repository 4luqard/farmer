#!/usr/bin/env python3
from kaggle_environments import make
import json

from main import *

env = make("kaggriculture", configuration={"episodeSteps": 10, "seed":13})
env.run([laziest_farmer, "random"])
with open("replay.json", "w") as f:
    json.dump(env.toJSON(), f)
