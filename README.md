# Kaggriculture
My unfinished solution for the [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) simulation competition on Kaggle.

## Status
Development has stopped. The agent, `laziest_farmer`, is a placeholder: it buys one wheat seed on
the first turn and passes on every turn after that. The plan was a hand-written heuristic driven by
forward simulation. The simulation helpers exist and have tests, but no heuristic or search uses them
yet. Each helper was built test-first as a walking skeleton, so it models only what `tests/` covers.

## Layout
| Path | Contents |
| :-- | :-- |
| `main.py` | Single-file agent: `laziest_farmer`, an opponent tracker and the forward-simulation helpers |
| `tests/` | pytest suite, one file per function |
| `docs/kaggriculture.md` | Game rules re-derived from the `kaggle-environments` 1.32.7 engine source |
| `docs/kaggriculture-deltas.md` | Where the competition's README and the engine disagree |
| `run_game.py` | Plays a 10-step local episode against the built-in `random` agent and saves `replay.json` |

## Forward simulation
| Function | Purpose |
| :-- | :-- |
| `_possible_actions(obs)` | Every action open to the farmer, each hired hand and the market this turn |
| `_clone_state(obs)` | Deep copy of an observation that preserves shared references |
| `_apply_action(obs, action_dict)` | The state one turn later, leaving `obs` untouched |
| `_is_terminal(obs)` | Whether the 720-turn season is over |
| `_get_reward(state)` | Money lead over the opponent once the season is over, else 0 |

`_opponent_tracker(obs)` summarises the opponent's farm and remembers it for the next step.

## Known gaps
- `_apply_action` simulates only the acting player. It does not model the opponent's turn, market
  price refreshes or decay of ongoing crops.
- Town-shop consumption fires one turn later than it does in the engine (`docs/kaggriculture-deltas.md`, section D).
- Kaggle runs the last callable in a submitted file as the agent, and `laziest_farmer` is not the
  last function in `main.py`.

## Running
Tested with Python 3.13, `kaggle-environments` 1.32.7 and `pytest` 9.

```bash
pip install kaggle-environments==1.32.7 pytest
python -m pytest tests/
python run_game.py
```

`python-kit/` is gitignored. It holds the competition's `README.md`, `AGENTS.md` and engine source,
all of which also ship with `kaggle-environments` under `kaggle_environments/envs/kaggriculture/`.
