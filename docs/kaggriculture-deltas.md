# Kaggriculture: where the shipped documentation and the engine disagree

Audit trail for [kaggriculture.md](kaggriculture.md).

**Compared:** the `README.md` shipped inside `kaggle-environments==1.32.7` at `kaggle_environments/envs/kaggriculture/README.md` (372 lines — the same document Kaggle distributes as the python-kit README) against the engine beside it, `kaggriculture.py` (1086 lines) and `kaggriculture.json`, plus the framework in `core.py` / `agent.py` / `utils.py`.

**Method:** every row below was read from the source and then confirmed empirically against a live 1.32.7 episode — 95 assertions plus a second measurement pass, all passing. Line references are 1.32.7 `kaggriculture.py` unless stated.

**One thing worth knowing first:** the 1.32.7 README is much closer to its engine than the 1.32.2 one was. If you built a model against 1.32.2's documentation, it asserted a goose cost of 200 (engine: 300), egg/milk/wool base prices of 80/240/300 (engine: 50/160/200), first-yield days of 3/6/5 for goose/cow/sheep (engine: 4/8/6), a CARE bonus of +2 (engine: +1), and no yield at all when an animal is unfed on a production day (engine: the base 1 still lands). All of those were corrected in the 1.32.7 README. What follows is what is *still* wrong or missing at 1.32.7.

---

## A. Contradictions — the README says something the engine does not do

| # | README (1.32.7) | Engine | Source |
| :-- | :---- | :---- | :---- |
| A1 | "Each turn, the player may take one action." (L35) | Every unit acts every turn — the farmer plus one op per hired hand — and market orders are submitted alongside them. The next section says so, contradicting this line. | `interpreter` 894-940 |
| A2 | "24 turns per day, and 30 days in the season - 720 total turns." (L35) | 720 states are *recorded*, but agents are polled 719 times and observe steps 0–718. The last recorded turn is a scoring frame nobody acts on. | 960; `core.py` step accounting |
| A3 | "Each harvest action will yield at least one unit of the crop." (L59) | `HARVEST` is a silent no-op when `yield_units` is 0, **and** when the plant is younger than its Time to First Yield — which one-time crops always look ready for, because they carry `yield_units = 1` from the moment they are planted. | 446-473; `_new_plant` 215 |
| A4 | The animal tile schema lists `"animal": "GOOSE" \| "COW" \| "SHEEP" \| None, # None until PLACEd` (L326) | An unoccupied structure has **no `animal` key at all** — `BUILD_COOP` writes exactly `{"kind": "COOP"}`. When an animal escapes the tile reverts to that same two-key form, discarding every other field. `tile["animal"] is None` is never true; test with `"animal" in tile`. | 496, 502, 819 |
| A5 | `max_lifespan_step` — "-1 for ongoing crops" (L317) | `-1` only until the ongoing crop fires its last scheduled production; it is then set to hour 0 of the following day, and decay begins. The Harvest Yields section describes this correctly, so the field comment contradicts the prose. | `_daily_refresh_plants` 800-802 |
| A6 | Turn Processing Order (L246-256) lists: action validation → player actions → market → town buys → "update observations" (day refresh, market refresh, income, farm update). | Four things are wrong. There is **no validation phase**. **Plant decay is missing entirely** — it runs every turn, after town consumption. The **day refresh is not an observation update**: it is a conditional phase that only runs on the last turn of a day, and it mutates the world. And "market refresh — modify the price of items based on sells from **previous** turn" is backwards: prices are recomputed within the same turn, after every order slot and again after town consumption. | 894-966; `_process_market` 628; `_town_consume` 750 |

---

## B. Omissions — mechanics the README never states

Each of these changes how a turn should be played or modelled.

**Costs and stores**

| # | Undocumented behaviour | Source |
| :-- | :---- | :---- |
| B1 | `FEED` consumes exactly **1 WHEAT**, taken from the acting unit's carried inventory. Wheat in the shed does not count; a unit next to a full shed still cannot feed. | 505-513 |
| B2 | `FERTILIZE` consumes exactly **1 FERTILIZER**, same store, same rule. | 475-482 |
| B3 | `SELL` draws **only from the shed**. Produce carried by a farmer or hand cannot be sold at all — it has to be dropped, placed, or carried to the automatic end-of-day dump first. | `_commit_unit` 653-660 |
| B4 | Purchases land in different places: `BUY_SEED` in the seed slot, `BUY_ANIMAL` and `BUY_PRODUCT` in the shed. An animal must then be picked up and placed before it produces anything. | 662-687 |
| B5 | A shed at `shedCapacity` **refuses** `BUY_PRODUCT` and `BUY_ANIMAL` outright, and the refusal aborts the rest of that order. The README only ever describes overflow being discarded. | 667, 682 |
| B6 | Fertilizer's "100" in the Object Types table is its market base price, not a fixed cost — it is bought with `BUY_PRODUCT` at the live price. And wheat has two prices: `BUY_SEED WHEAT` is a flat 10, `BUY_PRODUCT WHEAT` is the market price (25 at the start). | `MARKET_PARAMS` 41; `CROPS` 11 |
| B7 | Re-fertilizing inside an active window does not extend it: the expiry is `max(current, day + 2)`. | 481 |
| B8 | A `HIRE` you cannot afford is skipped silently and does **not** advance `hires_today`, so the next hire costs the same. | `_do_hire` 702-706 |

**Timing and ordering**

| # | Undocumented behaviour | Source |
| :-- | :---- | :---- |
| B9 | A hand hired this turn **cannot act this turn**. Market orders resolve after unit actions, so the hand exists only from the next turn onward. | 544 vs 894-940 |
| B10 | Town ticks are counted on the **global turn number**, not the hour: a tick fires whenever `step % interval == 0`. With defaults that is turns 0, 4, 8… for shops and 0, 24, 48… for the town center — the center's first purchase lands on the opening turn. Because consumption resolves *during* a turn, the effect first appears in the observation you receive on the **following** turn. | `_town_consume` 736, 745 |
| B11 | Units resolve **sequentially** — farmer first, then hands in list order — and each sees the tile as the previous unit left it. Two units watering the same plant means the second one wasted its turn. | 894-940 |
| B12 | Order-abort semantics: a unit that cannot commit (no money, empty shed, full shed) aborts **that order** and nothing else; later orders in the same list are still attempted. `HIRE` and `BUY_LAND` are atomic — resolved once per slot in player order, never entering the per-unit loop. Malformed orders are dropped when reached. | `_process_market` 544-628; `_parse_order` 631 |
| B13 | With default settings the 8-instance shop cap is reached on **day 24**, so the day-27 and day-30 unlock opportunities pass without adding anything. Town demand is fixed for the last fifth of the season. | 890-891, `MAX_SHOP_INSTANCES` 118 |
| B14 | Decay applies to whatever is left on the tile, so a plant harvested empty before its lifespan ends becomes a weed on the **first** decay tick instead of counting down. Leaving one unit unharvested buys two more turns. | `_decay_plants` 752-767 |

**Randomness**

| # | Undocumented behaviour | Source |
| :-- | :---- | :---- |
| B15 | All in-episode randomness comes from one generator per day, `random.Random((seed * 1_000_003) ^ day)`, consumed in a fixed order: player 0's weed rolls (row-major over the whole board), then player 1's, then the shop unlock draw. Because it is a **single shared stream**, the two farms never get the same weeds, and how many tiles player 0 has open changes what player 1 draws. A model that rolls weeds per-player independently diverges even with the right seed. | `_end_of_day` 871; `_spawn_weeds` 836 |
| B16 | Weeds spawn only on `None` tiles, so locked quadrants never grow them. Buying land is also buying a weed liability. | 838 |

**Observation surface**

| # | Undocumented behaviour | Source |
| :-- | :---- | :---- |
| B17 | The observation block omits two fields that are always delivered: `step` (global turn) and `remainingOverageTime` (your thinking-time bank). The README's own Quick Start reads `obs.get("step", 0)`. | `schemas.json`; measured |
| B18 | `market` gains a third key, `params`, holding the fully resolved price table — but only when `configuration["marketParams"]` was supplied. With defaults the key is absent. | `_new_market` 178-186 |
| B19 | Shop names in `unlocked_shops` are `BAKERY`, `PIZZA_SHOP`, `BRUNCH_SPOT`, `YARN_STORE`, `ICE_CREAM_SHOP`, `PET_CAFE`, `SMOOTHIE_SHOP`, `FARMERS_MARKET`. The README gives them only as prose ("Pizza Shop"). | `SHOPS` 103 |
| B20 | `DROP` is documented in the README but is **missing from the action description in `kaggriculture.json`**, which is what a machine reader would parse. | `kaggriculture.json` action.description |
| B21 | `BUY_LAND` unlocks quadrants in a fixed order — NE, then SW, then SE. The README gives the prices but not the sequence. | `LAND_ORDER` 96 |

**The framework layer — undocumented in its entirety**

| # | Undocumented behaviour |
| :-- | :---- |
| B22 | `actTimeout` is **1 second** here, and it is a soft budget: your function always runs to completion, and `max(0, duration - actTimeout)` is deducted afterwards from a **60-second** `remainingOverageTime` bank. You are disqualified only when one call's overrun exceeds the whole remaining bank. The deduction still applies on that turn, so the recorded bank goes negative despite a declared minimum of 0. |
| B23 | Returning garbage does **not** get you `INVALID`. The action schema is an unconstrained object, so any non-dict — a string, `None`, a list — is silently replaced by the default PASS action and the agent stays `ACTIVE`. Any dict passes as-is however malformed. `INVALID` is effectively unreachable. |
| B24 | A crashed (`ERROR`) or timed-out (`TIMEOUT`) agent is **resurrected at the terminal transition**: the interpreter overwrites every status to `DONE` and every reward to that player's money. An agent that raises on turn 3 still banks its money, provided the opponent survives to the end. Only mutual failure — every remaining active agent failing on the same turn — ends the episode early with both rewards `None`. |
| B25 | Shared observation fields are delivered to both agents from **player 0's** stored state. In a replay JSON, the `farms`/`market`/`town` stored under player 1 are not what player 1 was shown. |
| B26 | A submitted file is executed and the **last callable bound at module level** becomes your agent — a trailing `from math import sqrt` or a trailing `class Helper` silently replaces it. Arguments are sliced by declared parameter count, so `def agent(*args)` receives nothing. |
| B27 | `configuration["seed"]` is read once then set to `None` and stored on `env.info`; agents never see it. A replay resumes exactly only if `info` is passed back in. The built-in `random` opponent is unseeded, so runs against it never reproduce. |
| B28 | Three built-in opponents exist and are not listed anywhere in the README: `pass`, `random`, `starter`. |
| B29 | `env.step(actions)` bypasses agent timing entirely — no duration logged, no overage charged. A local harness driven that way never reproduces timeout behaviour. |

---

## C. What changed between 1.32.2 and 1.32.7

Relevant to anything modelled against the older engine or the older README. Framework files (`core.py`, `agent.py`, `utils.py`, `schemas.json`, `status_codes.json`) are **byte-identical** across the two releases; every change is inside the env.

| # | 1.32.2 | 1.32.7 |
| :-- | :---- | :---- |
| C1 | Price shapes were `linear, sq, sqrt, log, log10`. | A **`hinge`** shape is added: with `u = x/T`, `f(u) = u + 8·max(0, u−1)²`, normalised so `f(T) = 1`. `CARROT`, `TOMATO` and `EGG` switch their scarcity side to it. Carrot's `below_target` also moves 0.20 → **1.00**, taking `P(I0−T)` from $42 to **$70**; tomato and egg keep their targets and their curves are unchanged below the knee. |
| C2 | `townCenterSellInterval` default **12**. | Default **24** — once per day at `turnsPerDay = 24`. |
| C3 | Town-center demand ramped: ×1, then ×2 from day 10, ×4 from day 20 (`TOWN_CENTER_DEMAND_SCHEDULE`). | The schedule is **deleted**. Demand is a flat 1 of each non-fertilizer product per tick, all season. |
| C4 | Shops were drawn from those *not yet unlocked* — no duplicates. | Shops are drawn **with replacement** from the full table, capped at **8 instances**. A season can end with three yarn stores and no bakery, and each copy consumes independently. |
| C5 | `BUY_PRODUCT` / `BUY_ANIMAL` ignored the shed cap. | Both are **refused** once the shed holds `shedCapacity` items. |
| C6 | Movement onto a `LOCKED` tile was blocked. | Locked tiles are **passable**. Tile actions still no-op there. |
| C7 | The `LOCKED` guard ran before every op, so shed actions failed on a locked shed tile. | `PICKUP`, `DROP` and `PLACE`-into-shed now resolve **before** the guard and work from any of the four center tiles, locked or not — which matters because three of them start locked, and the first hand hired each day spawns on one. |

---

## D. Notes for this repo's forward model

`main.py` is already on 1.32.7 semantics — the `hinge` curve and its parameters, `_TOWN_CENTER_SELL_INTERVAL = 24`, `_SHED_CAPACITY = 100`, and the feed/fertilize costs of 1 all match the engine. Two follow-ups fall out of this audit:

**Resolved uncertainties.** `main.py:81-82` records that the FEED and FERTILIZE quantities were "inferred from tests" because the README does not state them — both are confirmed at 1 unit, drawn from the *acting unit's carried inventory* (B1, B2). `main.py:530` notes that "only `BAKERY` has a confirmed observation spelling" — all eight spellings in `_SHOP_DEMAND` are correct, and so is every demand quantity including the 2× on `YARN_STORE` and `PET_CAFE` (B19).

**One divergence found.** `_apply_town_consumption` (`main.py:1265`) documents `hour` and `day` as "before this turn's increment", i.e. the same incoming-step frame the engine uses. In that frame:

- the town center fires at `main.py:1290` on `hour % 24 == 0`, which matches the engine's `step % 24 == 0` — but only because `townCenterSellInterval` and `turnsPerDay` are both 24. Keyed off the hour rather than the global step, it stops matching if either is configured differently.
- the shops fire at `main.py:1295` on `turn % 4 == 1`, where the engine fires on `step % 4 == 0` — **one turn late**. The docstring explains the offset was chosen to match `tests/test_apply_action.py:test_town_shop_consumption` at "turn 97 = day 4 hour 1"; measured against the engine, shop ticks resolve on steps 72, 76, 80, 84, 88 and become *visible* at frames 73, 77, 81, 85, 89. The test appears to have been written from the visible frame and applied in the incoming-step frame. The town-center rule on the line above uses phase 0, so the two rules in the same function currently disagree with each other about the frame.

Nothing in `main.py` was changed here — this document is a docs-only change, and the fix belongs with its own test update.
