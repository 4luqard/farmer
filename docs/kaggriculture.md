# Kaggriculture

*Derived from the environment source in **kaggle-environments 1.32.7** — `kaggle_environments/envs/kaggriculture/{kaggriculture.py,kaggriculture.json}` plus the framework in `core.py` / `agent.py` / `utils.py`. Section order matches the README shipped with the environment so the two can be diffed; every rule here was read from the code and confirmed against a live episode. Where this document departs from the shipped README, the reason is itemised in [kaggriculture-deltas.md](kaggriculture-deltas.md).*

A farming sim where two players compete to maximize their income from farming by selling to a dynamic market.

## Overview

Each player starts with an empty farm and a small amount of income (seed money, if you will). Each turn, they can perform actions such as moving around the board, purchasing seeds or livestock, planting seeds, watering plants, harvesting produce or animal products, and selling that produce at the market. The game runs for a fixed amount of time representing one season, and the winner is determined by who has the most money in the bank at the end.

## Object Types

| Type | Yield Type | Seed Cost | Base Market Price | Time to First Yield | Time to Max Yield | Subsequent Yields | Max Yield | Action Cost | Yield / tile / day |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Wheat** | One-time | 10 | 25 | 2 days | 4 days | none | 6 (4 unfertilized) | 1 | 0.80 |
| **Carrot** | One-time | 20 | 35 | 2 days | 3 days | none | 4 (3 unfertilized) | 1 | 0.75 |
| **Tomato** | Ongoing | 50 | 60 | 8 days | 11 days | every day ×4 | 4 | 1 | 0.33 |
| **Strawberry** | Ongoing | 100 | 120 | 10 days | 16 days | every other day ×4 | 4 | 1 | 0.24 |
| **Melon** | One-time | 80 | 250 | 10 days | 10 days | none | 6 | 1 | 0.55 |
| **Goose/Egg** | Ongoing | 300 | 50 | 4 days | NA | every day, indefinitely | 4 held | 1 \+ 1 (build coop) | 1.00 |
| **Cow/Milk** | Ongoing | 400 | 160 | 8 days | NA | every two days, indefinitely | 6 held | 1 \+ 1 (build pasture) | 0.50 |
| **Sheep/Wool** | Ongoing | 500 | 200 | 6 days | NA | every three days, indefinitely | 6 held | 1 \+ 1 (build pasture) | 0.33 |
| **Fertilizer** | NA | 100 | X |  | X | X |  | 1 |  |

For crops, "Yield / tile / day" is total units harvested divided by the days the tile is occupied, watering daily and harvesting at peak yield. For animals it is the steady-state production rate (`1 / interval`) once the first yield lands; animals keep producing for as long as they are fed, so there is no fixed occupancy to divide by. "Max Yield" for animals is `max_held`, the cap on *unharvested* product sitting on the tile, not a lifetime total.

"Seed Cost" means different things per row, and the difference is worth internalising:

- **Crops** — a fixed price paid by `BUY_SEED`. It never moves with the market, and seeds never enter market inventory.
- **Animals** — a fixed price paid by `BUY_ANIMAL`, likewise market-independent.
- **Fertilizer** — *not* a fixed price. Fertilizer is bought with `BUY_PRODUCT` at the live market price, which happens to be its base of 100 at the starting inventory. It moves like any other price.

Wheat exists on both sides of that split: `BUY_SEED WHEAT` costs a flat 10, while `BUY_PRODUCT WHEAT` (the wheat you feed to animals) costs the market price, which starts at 25.

Crop "Time to Max Yield" is the age at which yield stops increasing under daily watering, which is not always the end of the bonus window:

- **Melon**'s bonus window is ages 6–12, but base 1 plus one unit per watered day reaches the cap of 6 at age 10, so ages 11–12 add nothing. Fertilizing reaches the cap at age 8.
- **Wheat** and **Carrot** only reach their listed Max Yield of 6 and 4 with fertilizer; watering alone peaks at 4 and 3.
- **Tomato** and **Strawberry** are ongoing but *not* indefinite: production is capped at 4 scheduled yields (tomato at ages 8–11, strawberry at ages 10, 12, 14, 16), after which the plant decays into a weed.

All plants must be watered every day. They will turn into weeds if they are not watered for two successive days. All animals must be fed every day using wheat. They will escape and be unrecoverable if they are not fed for two successive days. Wheat is also available to buy at the market and can be purchased at the current market price.

## Actions

Every unit you control acts every turn, and market orders are submitted alongside them. There are 24 turns per day and 30 days in the season, so `episodeSteps` is 720 — but the last recorded turn is a scoring frame that no agent acts on, so an agent makes **719 decisions, numbered 0 through 718**. See [Episode Lifecycle & Limits](#episode-lifecycle--limits).

An action is a single dict with three independent parts:

```py
{
  "farmer": ["WATER"],                       # the main farmer's op
  "hands":  [["NORTH"], ["HARVEST"]],        # one op per hired hand, positionally matched
  "market": [["SELL", "CARROT", 4]],         # up to maxMarketOrdersPerTurn orders
}
```

`hands` is matched positionally against `farms[player]["hands"]`. Entries past the number of hands you actually have are ignored, and a missing entry leaves that hand idle. Any of the three keys may be omitted.

### Farmer / Farm Hand Action

Each Farmer / Farm Hand can be given an action every turn. Farmer/Farm Hand CAN occupy the same space.

Units resolve **in order** — the farmer first, then hands in list order — and each one sees the tile as the previous unit left it. Two units on the same plant both issuing `WATER` means the second one is a no-op; two units digging the same weed means the second one digs bare ground.

#### Movement

- NORTH, SOUTH, EAST, WEST — Move one cell in that direction. Moves off the edge of the board are no-ops. Locked tiles are passable: a unit may move onto and across unbought quadrants, but tile actions (`PLANT`, `WATER`, `BUILD_*`, etc.) all no-op on a locked tile and consume nothing. The exception is the shed actions `PICKUP`, `DROP`, and `PLACE`-into-shed, which work from any shed-access tile even while that tile is locked — they use the tile only as a standing position and never change it.

#### Shed

Picks up an item from the shed (must be orthogonally adjacent) into the inventory

- PICKUP `<item>` `[n]` — move up to `n` of `<item>` (default 1) from the shed into the active farmer/hand's inventory. `n` is clamped to what the shed actually holds. Any item present in the shed is valid (animals, fertilizer, harvested produce, etc.). Seeds live in a separate slot and are never picked up — `PLANT` consumes them directly.
- DROP — orthogonally adjacent to the shed, dump the active farmer/hand's entire current inventory into the shed. Overflow past `shedCapacity` is discarded. No-op if not shed-adjacent.

#### Plants

- PLANT `<crop>` — Plant a seed purchased from the market
  - Seeds are automatically available to all Farmers / Farm Hands
  - The tile must be empty (`None`). Planting on a plant, weed, structure, or locked tile is a no-op.
  - If you try to plant too many in a specific turn, none are planted
    - ie if you have 1 melon seed, but two units do the PLANT MELON command
    - The rejection is per crop and all-or-nothing: with 1 melon seed and 2 melon planters, *both* melon commands become PASS and the seed is not spent. Requests for other crops in the same turn are unaffected.
- WATER — Water a plant. This only needs to be done once per day, and subsequent waterings on the same day are a no-op.
- HARVEST — Gather produce from a plant. If the plant does not have subsequent yields, it will be removed from the map. Harvested items are added to the acting unit's inventory. Two conditions must both hold or the action is a silent no-op that wastes the turn:
  - `yield_units` on the tile must be greater than 0.
  - The plant's age (`day - planted_day`) must have reached its Time to First Yield. A one-time crop carries `yield_units = 1` from the moment it is planted, so an early `HARVEST` looks legal and still does nothing.
- FERTILIZE — Fertilize a plant to increase its potential yield (see harvest yields below).
  - Costs **1 FERTILIZER**, taken from the acting unit's carried inventory. Fertilizer sitting in the shed does not count; a unit must `PICKUP` it first. With no carried fertilizer the action is a no-op.
  - Doubles the per-day yield bonus for the next 3 days — the current day plus the two after it. The bonus only applies on days the plant is also watered (basic needs first).
  - Re-fertilizing inside an active window does not extend it: the expiry is `max(current expiry, day + 2)`, so a second application only helps once the first has nearly lapsed.

#### Animals

- PLACE `<item>` `[n]` — Drop items from the active farmer/hand inventory into either a tile or the shed:
  - **Animal placement**: standing on a matching unoccupied structure (`GOOSE` on a coop, `SHEEP`/`COW` on a pasture) places one animal from inventory onto the tile. The `n` argument is ignored.
  - **Shed drop**: standing orthogonally adjacent to the shed moves up to `n` (default 1) of `<item>` from inventory into the shed. Capped by `shedCapacity`; excess stays in inventory.
- FEED — Feed an animal, once per day. Costs **1 WHEAT**, taken from the acting unit's carried inventory — not from the shed. A unit standing next to a shed full of wheat still cannot feed until it has picked some up. With no carried wheat the action is a no-op and the animal stays unfed.
- HARVEST — Collect the eggs/milk/wool produced by the animal. No-op when `yield_units` is 0.
- COLLECT\_FERTILIZER — Collect 1 fertilizer from the animal. Every surviving animal makes 1 available at the end of each day, whether or not it was fed or cared for. Uncollected fertilizer does not accumulate, so an animal left alone for five days still yields 1 unit.
- CARE — Care for an animal (once per day, no-op if already cared for). See animal care below.

#### Animal Care

CARE banks a yield bonus that is paid out on the animal's next scheduled production:

* At end of day, if the animal was both fed AND cared for that day, `pending_care_bonus` increments by 1. Days where the animal was unfed do not bank a bonus (basic needs first).
* On a scheduled production day, if the animal is fed, the entire banked bonus is added to that production's yield (in addition to the base 1) and the bank resets to 0.
* If the animal is unfed on the production day, the base 1 unit is still produced, but the banked bonus is not applied and the bank resets to 0.
* Production is resolved before the day's banking, so caring on a production day feeds the *next* one, never that day's.
* `pending_care_bonus` is capped indirectly by the per-animal `max_held` cap on `yield_units`.

#### Terrain

- BUILD\_COOP \- adds a coop to an unoccupied tile. Free; costs only the turn.
- BUILD\_PASTURE \- add pasture to an unoccupied tile. Free; costs only the turn.
- DIG — Remove a plant from a square to free up space OR remove a weed from a square (does not yield any produce) OR remove an **empty** goose coop / pasture. A coop or pasture with an animal on it cannot be dug; the DIG is a no-op.

#### Other

- PASS — Default if there is nothing to do (optional)

### Market Action

Each turn you can submit up to `maxMarketOrdersPerTurn` (default 10) market actions; any orders past that limit are silently dropped. This is an ordered list and market orders will be processed in order simultaneously (one from each player) while both players have orders.

- BUY\_SEED — Purchase N units of a single item from the market. Fixed price, unlimited supply, and the seeds land in your **seed slot** (`private.seeds`), never the shed.
  - BUY\_SEED WHEAT 1
- BUY\_ANIMAL — Fixed price, unlimited supply. The animal lands in **the shed** as an item; a unit must `PICKUP` it and `PLACE` it on a matching structure before it starts producing.
  - BUY\_ANIMAL GOOSE 1
- BUY\_PRODUCT — Only `WHEAT` and `FERTILIZER` may be bought. Dynamic price. The goods land in **the shed**.
  - BUY\_PRODUCT WHEAT 1
  - BUY\_PRODUCT FERTILIZER 1
- SELL — Sell N units of a single item to the market. Sold goods come **only from the shed**. Produce still being carried by a farmer or hand cannot be sold — it has to reach the shed first, by `DROP`, by `PLACE`, or by the automatic end-of-day drop.
  - SELL WHEAT 1
- HIRE — Hire a farm hand for the day. Cost increases for each extra hand hired on the same day. The hand appears at the end of this turn's market phase, which is *after* unit actions have already resolved, so **a hand cannot act on the turn it was hired** — its first orders are obeyed on the following turn.
- BUY\_LAND \- unlock a new 5x5 segment of land to plant on. Increasing in cost. Quadrants unlock in a fixed order — NE, then SW, then SE — regardless of which one you would prefer.
  - Costs are: $1k, $2k, $4k

Every order fails silently rather than erroring. An order stops early — and the rest of *that* order is abandoned — as soon as one unit of it cannot be committed: not enough money, an empty shed on a `SELL`, or a shed already at `shedCapacity` on a `BUY_PRODUCT`/`BUY_ANIMAL`. Later orders in the same list are still attempted. A malformed order (unknown op, missing quantity, quantity ≤ 0, an item the op does not accept) is dropped when it is reached.

## Watering / Animal Feed

Plants (and animals) must be watered/fed a minimum of every other day. Watering only needs to be done once per day, and subsequent watering actions are a no-op. In the case of plants not watered for two consecutive days, at the end of the day they turn into a WEED. In the case of animals they escape (unrecoverable).

A new seed starts with `consecutive_unwatered = 1` — the planting day itself counts as the first missed day. A seed planted and left unwatered that same day reaches 2 at the end-of-day refresh and becomes a weed that night, before it grows. There is no grace period for fresh plantings.

A newly placed animal starts with `consecutive_unfed = 0`, so it survives its first day unfed.

When an animal escapes, the structure survives: the tile reverts to a bare `{"kind": "COOP"}` or `{"kind": "PASTURE"}` and can be restocked with another `PLACE`. Every other field on the tile — accumulated `yield_units`, `pending_care_bonus`, `fertilizer_available` — is discarded with the animal.

Every unit is teleported back to the shed at the start of each day, so a plant or animal far from the centre needs a unit to walk out to it again every single morning. Watering routes, not just watering, are the constraint.

Note that watering one-time yield plants during their yield window results in a higher yield. This is NOT true for ongoing yield plants/animals. See below.

## Harvest Yields

Plants will potentially have higher yields based on how well they have been cared for.

* **One-time crops** (wheat, carrot, melon): planted with 1 unit already on the tile. Starting at half the plant's `max_yield_day` (Time to Max Yield) rounded up, and ending at `max_yield_day` itself, watering during the bonus window will add one unit per day to the total harvestable yield.
  * Fertilized plants add 2 per day instead.
  * The running total is clamped to the crop's Max Yield, so days past the cap add nothing.
* **Ongoing crops** (tomato, strawberry): Scheduled production happens at fixed intervals, resolved at end of day. The base yield is 1 per scheduled production. If the plant is fertilized AND watered that day, yield is doubled to 2. The total is clamped to Max Yield, which is a cap on *unharvested* units sitting on the tile.
* Once a plant has hit its maximum lifespan, the total yield available on the plant will reduce by 1 every other turn until it hits 0, at which point the plant becomes a weed.
  * **One-time crops** reach max lifespan one day after `max_yield_day`, at hour 0 of that day.
  * **Ongoing crops** start decay one day after their cumulative production count reaches `max_yield` (i.e. they've fired enough scheduled productions to hit the cap, regardless of whether the produce has been harvested).
  * Decay applies to whatever is left on the tile, so a plant harvested empty before its lifespan ends becomes a weed on the *first* decay tick rather than counting down. Leaving one unit unharvested buys two more turns.

## Map Features

Each player has their own farm with a set number of squares. Players are unable to see the state of the other’s shed, but can see the state of their opponent’s farm.

### Farm Space

- The land near your farm is a `boardSize` × `boardSize` grid (default 10×10), divided into four 5×5 quadrants. At first, your farm covers one quadrant (25% of the squares) — always NW. For an increasingly large fee, you can buy the neighboring quadrants and eventually cover 100% of the squares.
- Each plant or animal occupies one square on the farm.
- Players can allocate these squares however they choose between crops and livestock. There are no specific limits per type.
- Weeds have a chance of spawning on any empty cells on the farm, and must be cleared before the land can be used for other purposes. Locked tiles never grow weeds — buying land is also buying a weed liability.
- Squares on the farm can be either a plant, a coop/pasture, a weed, or empty.

### Shed (Inventory)

- Functions as an inventory for items that are harvested but not yet sold, or for seeds that have not yet been planted
- Farmer and hired farm hands will spawn at the shed at the start of each day
- Farmer and hired farm hands drop their inventory at the end of the day in the shed (if there is room)
- Limited to 100 items, excluding seeds. Once the shed is full, any further items added (via `PLACE` mid-day or end-of-day inventory drop) are discarded — there is no overflow holding area, so stockpiling on farmer/hand inventories does not bypass the cap.
- A full shed also blocks purchases: `BUY_PRODUCT` and `BUY_ANIMAL` are refused outright once the shed holds `shedCapacity` items, and the refusal aborts the rest of that order. `BUY_SEED` is unaffected, because seeds are not shed items.
- The cap counts every non-seed item together — harvested produce, fertilizer, and animals waiting to be placed all draw on the same 100.

The shed sits at the center of the board and is not a tile — it never appears in the `tiles` array, whose only values are `None`, `"LOCKED"`, and structure dicts. "Orthogonally adjacent to the shed" means standing on one of the four center tiles, `(half-1, half-1)`, `(half, half-1)`, `(half-1, half)`, `(half, half)` for `half = boardSize // 2`. At the default `boardSize = 10` those are `(4,4)`, `(5,4)`, `(4,5)`, and `(5,5)`, one in each quadrant. Since only NW starts unlocked, three of those four tiles begin locked; the shed is reachable from all of them regardless, because the shed itself is never locked.

### Farmer/Farm Hand

#### Hiring

- Hiring is a market order (`HIRE`). It costs more every time you want to hire an additional hand each day. At the end of the day all, hands drop inventory at the farm and disappear (need to be re-hired each day)
- Cost is `farmHandCostMult * fib(n)` where `n` is the number of hires already made today (fib starts 1, 1, 2, 3, 5, 8, 13, ...).
  - With the default `farmHandCostMult = 1`: 1, 1, 2, 3, 5, 8, 13, 21, etc… (resets at the start of each day)
  - A hire you cannot afford is skipped silently; it does not advance the counter, so the next one costs the same.
  - The counter lives in `farms[player]["hires_today"]`, so the price of your next hand is always visible in the observation.
- A hired hand appears orthogonally adjacent to the shed in a free space following NWSE. If there are not open spaces, it looks for the one with the least occupants, breaking ties by NWSE preference
- Spawn placement ignores whether the tile is locked. Since the main farmer starts on `(4,4)`, the least-occupied rule sends the first hire of each day to `(5,4)`, which is locked until the NE quadrant is bought. Locked tiles are passable, so a hand spawned on one can move back to unlocked land.
- Hands hired this turn are idle this turn. Budget one turn of travel before they are useful.

#### Inventory

- When harvesting or picking items up, they are added to inventory.
- Can drop items in the shed
- Carried items cannot be sold. The market reads the shed only.
- At the end of the day, all items in all inventory will be added to shed inventory (if there is room). Anything that doesn't fit is discarded — overflow is lost.

### Town Buildings

As the season progresses, new shops unlock at regular intervals (every `townShopUnlockInterval` days, default 3). Each unlock is drawn uniformly at random **with replacement** from the full shop table, so the same shop can unlock more than once — a season might end up with three bakeries and no yarn store. Once unlocked, a shop stays active for the rest of the game, and unlocking stops after 8 total instances. Total demand grows monotonically as more shops unlock.

The unlock happens during the end-of-day refresh, so the new shop is already present in the observation at hour 0 of days 3, 6, 9, … At the default settings the 8-instance cap is reached on day 24, and the two remaining unlock opportunities (days 27 and 30) pass without adding anything. Demand is therefore fixed for the last fifth of the season.

Each unlocked shop *instance* consumes one of every product it demands every `townShopSellInterval` turns (default 4). So with the default interval, a shop demanding wheat removes 6 wheat from the market per day, and two copies of that shop remove 12. Single-product shops consume 2x.

In addition, the town center consumes one of every product (excluding fertilizer) every `townCenterSellInterval` turns (default 24, i.e. once per day). This rate is flat for the whole season — it does not ramp.

Both kinds of tick are counted on the global turn number, not on the hour within the day: a tick fires on every turn where `step % interval == 0`. With the defaults that is turns 0, 4, 8, … for shops and turns 0, 24, 48, … for the town center — the town center's first purchase happens on the opening turn, before either player can have produced anything. Because consumption is resolved while the turn is being processed, the change first appears in the observation you receive on the *following* turn.

| Shop Type | Increases Demand For |
| :---- | :---- |
| Bakery | eggs, wheat  |
| Pizza Shop | milk, tomatoes, wheat |
| Brunch Spot | eggs, wheat, strawberries |
| Yarn Store | wool (2x) |
| Ice Cream Shop | strawberries, milk, wheat |
| Pet Cafe | carrots (2x) |
| Smoothie Shop | strawberries, milk |
| Farmers Market | wheat, carrots, tomatoes, strawberries |

Shop names appear in `town.unlocked_shops` in `SCREAMING_SNAKE_CASE`: `BAKERY`, `PIZZA_SHOP`, `BRUNCH_SPOT`, `YARN_STORE`, `ICE_CREAM_SHOP`, `PET_CAFE`, `SMOOTHIE_SHOP`, `FARMERS_MARKET`.

## Market Mechanics

The market has an unlimited supply of seeds and animals at fixed prices. Sell prices, however, move dynamically per resource and persist across days.

Every product (and fertilizer) starts the game with a market inventory of `I0 = 10,000` units, far above any single game's realistic production volume so that inventory is essentially guaranteed to stay positive. The sell price for a product is `base` at `I0`, rises as inventory falls (players buying or town consumption draining supply), and falls as inventory grows (players selling).

### Selling inventory to the market

Players can queue any number of sell or buy orders (for any quantity) in the market action list. Orders are processed concurrently across players, one unit at a time. For example, when both players issue `SELL CARROT 10` first, we take the current carrot price, give both players that price for their first carrot, then add 2 carrots to the market (1 from each player) — which may shift the price — and repeat until both orders complete.

If the sell price has been driven down to `$1` (the price floor), the unit is still purchased but is *not* added to market inventory, so the floor remains responsive to subsequent buys.

The lockstep is per order *slot*: both players' first orders are worked through together, then both players' second orders, and so on. `HIRE` and `BUY_LAND` are the exception — they are atomic, resolved once at the top of their slot in player order, and never enter the per-unit loop. Prices are recomputed after each slot finishes, and once more after town consumption, so the `prices` you see in an observation are always current for the inventory shown beside them.

### Buying inventory from the market

Only `WHEAT` and `FERTILIZER` can be bought from the market via `BUY_PRODUCT` (other products are sold at the market but not bought back). Selling is unrestricted: every product, including fertilizer collected from animals, can be sold via `SELL`. Two things drain market inventory: town buildings (town center and shops, which consume products for free) and player `BUY_PRODUCT` orders. Buy orders follow the same one-unit-at-a-time concurrent procedure as sell orders. If a player runs out of money mid-order, the order is stopped.

The buy price is quoted at the post-buy inventory and the sell price is quoted at the pre-sell inventory, so an immediate buy followed by a sell of the same item against an otherwise-unchanged market nets exactly zero.

Money can never go negative: any unit of an order you cannot afford is refused and the order stops there.

### The Price Function

For each resource the curve is defined by a base price, an anchor throughput `T`, and an independent **shape function** + **target move** for each side of the equilibrium:

```
price(inv) = base + sign · amp · f(|inv − I0|)
  sign = +1  if inv < I0   (scarcity → price up)
  sign = −1  if inv > I0   (glut    → price down)
  amp  = target · base / f(T)        (derived; not stored)
  f    ∈ { linear, sq, sqrt, log, log10, hinge }   (log uses ln(1+x), so f(0)=0)
```

Floored at `$1` and rounded to the nearest dollar.

`hinge` is the one shape that depends on `T` rather than on `x` alone: with `u = x / T` it evaluates to `u + 8 · max(0, u − 1)²`. Below `T` it is linear in `u`; above `T` the quadratic term takes over and the price climbs steeply. Since `f(T) = 1` by construction, `target` keeps its usual meaning. (`hinge` degenerates to plain `linear` if a custom `marketParams` entry sets `T` to zero or omits it.)

`T` is the production capacity of a single 5×5 field over a 24-day window at optimal watering with no fertilizer (animal totals are pre-discounted by 30% to account for wheat-feed overhead, and allow one day to build the coop or pasture). The 24-day window is a calibration horizon, not the 30-day season length. It is shorter on purpose: the opening days are setup-heavy and yield little.

`target` says "moving `T` units past `I0` shifts the price by `target × base`." Picking different `f` and `target` on each side lets resources with similar production profiles play very differently strategically — wheat panics on scarcity but absorbs gluts; melon barely reacts to scarcity but crashes hard on overproduction; wool mirrors melon at a smaller scale. Premium resources (base > $100: strawberry, melon, milk, wool) use `above_target > 1`, so even modest gluts drive them straight to the $1 floor — bundling and timing sales matters more for these than for staples.

Carrot, tomato and egg use `hinge` on the scarcity side, so their prices stay near base under ordinary demand and rise sharply once demand runs past `T`. The town shops that consume them are listed in `unlocked_shops`.

- **Carrot** — `hinge` at `below_target` 1.00. Consumed by pet cafes (single-product, so each consumes double) and farmers markets.
- **Tomato** — `hinge` at `below_target` 0.40. Consumed by pizza shops and farmers markets.
- **Egg** — `hinge` at `below_target` 0.40. Consumed by bakeries and brunch spots.

Tomato and egg keep the `below_target` of the `linear` curves they replaced. Because `linear`'s amplitude already normalises to `x / T`, which is exactly `hinge`'s below-knee branch, their prices from `I0` down to `I0 − T` are unchanged; the curves differ only past the knee.

| Resource | Base | I0 | T | Below func | Below target | Above func | Above target | P(I0−T) | P(I0+T) | P(I0+2T) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **Wheat** | 25 | 10,000 | 400 | sqrt | 0.80 | log | 0.20 | $45 | $20 | $19 |
| **Carrot** | 35 | 10,000 | 450 | hinge | 1.00 | sqrt | 0.70 | $70 | $10 | $1 |
| **Tomato** | 60 | 10,000 | 200 | hinge | 0.40 | sqrt | 0.60 | $84 | $24 | $9 |
| **Strawberry** | 120 | 10,000 | 100 | sqrt | 0.70 | linear | 1.60 | $204 | $1 | $1 |
| **Melon** | 250 | 10,000 | 300 | log | 0.20 | sq | 3.60 | $300 | $1 | $1 |
| **Egg** | 50 | 10,000 | 332 | hinge | 0.40 | log | 0.20 | $70 | $40 | $39 |
| **Milk** | 160 | 10,000 | 122 | sqrt | 0.60 | linear | 1.60 | $256 | $1 | $1 |
| **Wool** | 200 | 10,000 | 105 | log | 0.20 | sq | 3.20 | $240 | $1 | $1 |
| **Fertilizer** | 100 | 10,000 | 200 | linear | 0.40 | linear | 0.40 | $140 | $60 | $20 |

The defaults live in `MARKET_PARAMS` in `kaggriculture.py`. Per-resource overrides (sparse: any subset of `base`, `I0`, `T`, `below_func`, `below_target`, `above_func`, `above_target`) can be supplied at episode creation via `env.configuration["marketParams"]` without touching code, e.g. `{"WOOL": {"above_target": 0.95}}`. Supplying any override also adds a `params` key to the `market` observation holding the fully resolved parameter table; with default parameters that key is absent.

## Turn Processing Order

One turn is resolved in this order. Everything in steps 1–5 happens before any agent sees the result, so the observation you receive at turn *N* reflects every phase of turn *N−1*.

1. **Unit actions** — player 0's farmer, then player 0's hands in order, then player 1's the same way. Actions mutate the farms directly and in sequence; there is no simultaneity within a player. The only cross-unit rule is the atomic `PLANT` check, which is applied per player before any of that player's units move: if the units request more seeds of a crop than the player holds, every `PLANT` of that crop is replaced by `PASS`.
2. **Market orders** — both players' queues are truncated to `maxMarketOrdersPerTurn` and worked slot by slot, as described under Market Mechanics. Money moves here, and prices are refreshed at the end of every slot.
3. **Town consumption** — town center and shops reduce market inventory on their tick schedule, and prices are refreshed again.
4. **Plant decay** — every plant past its maximum lifespan loses a yield unit on alternating turns, and becomes a weed at zero.
5. **End of day** — only on the last turn of a day, i.e. when `(step + 1) % turnsPerDay == 0`. Per player, in this order: plant refresh (watering check, weeds, ongoing production) → animal refresh (feeding check, escapes, production, care banking, fertilizer availability) → weed spawning on empty tiles → every carried inventory dumped into the shed → the farmer returned to the shed, all hands dismissed, `hires_today` reset to 0. Then one shop unlock is rolled for the town.
6. **Clock advance** — `day` and `hour` are recomputed from the new step: `day = step // turnsPerDay`, `hour = step % turnsPerDay`.

There is no action-validation phase. Illegal unit actions are silent no-ops that consume the turn, and malformed market orders are dropped when reached; neither produces an error or a status change. See [Action Validation & Agent Status](#action-validation--agent-status).

## Win Conditions

The win condition is simple- whoever has the greatest number of coins at the end of the season is the winner. It is also possible that the two players will tie.

## Reward

The player who has the most money in the bank at the end of the game wins. Unsold items in the inventory do not count towards that total.

The reward is written once, on the final transition, as the player's `money` at that instant. Nothing is settled afterwards: produce in the shed, seeds in the seed slot, animals waiting to be placed, and land you bought are all worth exactly nothing at scoring time. A sale that would have happened on turn 719 never happens, because turn 718 is the last turn anyone acts on.

## Observation Format

The top-level observation passed to each agent:

```py
{
  "player": int,           # 0 or 1
  "step":   int,           # global turn number, 0-indexed (supplied by the framework)
  "day":    int,           # 0-indexed in-game day
  "hour":   int,           # 0-indexed turn within the day
  "remainingOverageTime": float,   # seconds of banked thinking time left (this player only)
  "farms":  [farm, farm],  # public per-player state, indexed by player id (shared)
  "market": {              # shared
    "inventory": { "WHEAT": int, "CARROT": int, ... },
    "prices":    { "WHEAT": int, "CARROT": int, ... },
    # "params": {...}      # present only when configuration["marketParams"] was supplied
  },
  "town": {                # shared
    "unlocked_shops": ["BAKERY", "BAKERY", ...],   # may repeat; each entry consumes independently
  },
  "private": {             # this player only; opponent's private state is not visible
    "shed":        { "WHEAT": int, "GOOSE": int, "FERTILIZER": int, ... },
    "seeds":       { "WHEAT": int, "CARROT": int, ... },
    "inventories": [farmer_inv, hand_inv, ...],  # [0] is the main farmer
  },
}
```

`shed` always carries a key for all nine products plus the three animals, zero-filled; `seeds` always carries all five crops. `inventories` starts as `[{}]` and grows by one empty dict per hand hired that day. Individual carried inventories are sparse — an item at zero is deleted rather than kept at 0.

Each `farm` dict (public, visible to both players):

```py
{
  "money":              float,
  "tiles":              [[tile, ...], ...],   # tiles[y][x]
  "farmer":             [x, y],
  "hands":              [[x, y], ...],         # hired hands for the current day
  "unlocked_quadrants": ["NW", ...],          # subset of {"NW","NE","SW","SE"}
  "hires_today":        int,                  # used to price the next HIRE
}
```

A `tile` is one of:

- `None` — empty unlocked tile
- `"LOCKED"` — tile in a quadrant the player has not yet bought
- a plant dict:
  ```py
  {
    "kind":                 "PLANT",
    "crop":                 "WHEAT" | "CARROT" | "TOMATO" | "STRAWBERRY" | "MELON",
    "planted_day":          int,
    "watered_today":        bool,   # reset to False each end-of-day
    "consecutive_unwatered": int,   # 2+ → tile turns to a weed
    "yield_units":          int,    # units currently harvestable
    "max_lifespan_step":    int,    # step at which decay begins; -1 until it is known
    "fertilized_until_day": int,    # last day fertilizer bonus applies; -1 if none
  }
  ```
  `max_lifespan_step` is fixed at planting for one-time crops. For ongoing crops it stays `-1` until the plant fires its last scheduled production, and is then set to hour 0 of the following day.
- a weed dict: `{"kind": "WEED"}`
- an **empty** coop or pasture, which is exactly two keys and nothing else — there is no `animal` key set to `None`:
  ```py
  {"kind": "COOP"}      # or {"kind": "PASTURE"}
  ```
- an occupied structure:
  ```py
  {
    "kind":                 "COOP" | "PASTURE",
    "animal":               "GOOSE" | "COW" | "SHEEP",
    "placed_day":           int,
    "yield_units":          int,
    "fed_today":            bool,
    "consecutive_unfed":    int,    # 2+ → animal escapes
    "cared_today":          bool,
    "fertilizer_available": bool,   # set at end-of-day for every surviving animal; cleared by COLLECT_FERTILIZER
    "pending_care_bonus":   int,    # banked CARE bonus, applied on the next yield tick
  }
  ```
  Test occupancy with `"animal" in tile`, not `tile.get("animal") is not None` — an empty structure has no such key, and when an animal escapes the tile reverts to the two-key form.

`farms` is shared state: both players read the same list, so `farms[obs["player"]]` is your farm and `farms[1 - obs["player"]]` is your opponent's. `private` is yours alone; there is no way to see the opponent's shed, seeds, or carried inventories.

## Quick Start

```py
from kaggle_environments import make


def my_agent(obs):
    # Buy one wheat seed on the very first turn, then PASS forever after.
    if obs.get("step", 0) == 0:
        return {"farmer": ["PASS"], "market": [["BUY_SEED", "WHEAT", 1]]}
    return {"farmer": ["PASS"], "market": []}


env = make("kaggriculture", configuration={"episodeSteps": 200})
env.run([my_agent, "random"])
env.render(mode="ipython", width=800, height=800)
```

## Configuration Defaults

Per-crop seed costs and per-product base prices are not configurable; they are documented in the Object Types and Price Function tables above. The configurable knobs are:

| Parameter | Default | Description |
| :---- | :---- | :---- |
| episodeSteps | 720 | Total recorded turns in the season (24 turns × 30 days). Agents act on turns 0–718; turn 719 is scoring only |
| actTimeout | 1 | Seconds allowed per decision before the overage bank is charged |
| runTimeout | 1200 | Wall-clock seconds for the whole episode |
| boardSize | 10 | Width and height (in tiles) of each player's square farm. Advanced uses 10 = four 5x5 quadrants |
| startingMoney | 3000 | Coins each player starts with |
| maxMarketOrdersPerTurn | 10 | Maximum number of market orders processed per player per turn; extras are silently dropped |
| turnsPerDay | 24 | Number of turns that make up one in-game day |
| shedCapacity | 100 | Max non-seed items the shed can hold; overflow at end-of-day drop is discarded, and purchases are refused once it is reached |
| weedSpawnChance | 0.005 | Per-tile probability of a weed spawning on an empty unlocked tile during end-of-day refresh |
| townShopUnlockInterval | 3 | Days between successive town shop unlocks (drawn with replacement, capped at 8 instances) |
| townShopSellInterval | 4 | Turns between consumption ticks by every unlocked town shop instance |
| townCenterSellInterval | 24 | Turns between consumption ticks by the town center (flat rate, once per day) |
| farmHandCostMult | 1 | Multiplier on the Fibonacci hire-cost sequence |
| marketParams | {} | Sparse per-resource price-curve overrides |
| seed | null | Optional input seed for deterministic episode generation; cleared from config after read so it stays out of agent observations |

`actTimeout` and `runTimeout` come from the framework's base schema; `kaggriculture.json` overrides `actTimeout` to 1 and leaves `runTimeout` at its default. Both are delivered to your agent in the configuration argument. `maxLogLength` is read by the framework but is not a declared key, so it stays at its built-in default of 10,000 characters.

---

*The sections below are not part of the environment's shipped README. They document behaviour that lives in the framework (`core.py`, `agent.py`, `utils.py`) or in corners of the interpreter that the rules text does not reach, and that decides real matches.*

## Episode Lifecycle & Limits

**An episode records `episodeSteps` states and takes `episodeSteps - 1` decisions.** With the default 720, `env.steps` has indices 0 through 719, and `env.steps[k][0].observation["step"] == k`. Index 0 is the freshly initialised world, and its recorded action is the schema default rather than anything an agent chose. Agents are polled 719 times and observe steps 0 through 718.

The last turn any agent acts on is **718**. The interpreter watches for the incoming step reaching `episodeSteps - 2` and, on that transition, sets every agent to `DONE` and writes each reward as that player's `money`. The framework independently forces `DONE` on any still-active agent once a state at index `episodeSteps - 1` exists. The interpreter is never invoked with an incoming step of 719.

The practical consequence for a search agent: your horizon is 719 plies, not 720, and any plan whose payoff lands on the final turn pays out one turn too late.

**Timing is a soft budget with a hard bank.**

- `actTimeout` (1 second here) is not enforced with a kill. Your function always runs to completion; only afterwards is the elapsed time compared against the budget.
- Every turn, `max(0, duration - actTimeout)` is deducted from `remainingOverageTime`, which starts at **60 seconds** and is visible in your observation. A 1.3-second turn costs 0.3 seconds of bank and is otherwise fine.
- You are disqualified only when a *single* call's overrun exceeds the entire remaining bank. At that point your action is discarded — replaced with nothing, not with a PASS — and your status becomes `TIMEOUT`.
- The deduction is applied even on the disqualifying turn, so the recorded bank goes negative despite the schema declaring a minimum of 0. Do not rely on it being non-negative.
- `runTimeout` (1200 seconds) is checked only between turns. If the episode exceeds it, the run is abandoned mid-episode: no `DONE`, no rewards, nothing scored.
- Driving the environment yourself with `env.step(actions)` bypasses agent timing entirely — no duration is logged and no overage is charged. Local forward-model harnesses therefore never reproduce timeout behaviour.

## Action Validation & Agent Status

The status of each agent is one of `INACTIVE`, `ACTIVE`, `DONE`, `ERROR`, `INVALID`, `TIMEOUT`.

**Returning nonsense does not get you disqualified.** The action schema for this environment is an unconstrained object, so the framework's schema pass replaces anything that is not a dict — a string, `None`, a list — with the default action `{"farmer": ["PASS"], "hands": [], "market": []}` and lets it through. Any dict passes as-is, however malformed its contents. `INVALID` is effectively unreachable here; an agent that returns garbage every turn stays `ACTIVE` and quietly passes for the whole season.

**Illegal game actions are silent no-ops.** Walking into the void, watering bare earth, harvesting an immature plant, feeding with no wheat, planting on an occupied tile — all are accepted, do nothing, and consume the unit's turn. Nothing in the observation marks them as rejected. The only defensive rule is the atomic `PLANT` check described under Actions.

**`ERROR` and `TIMEOUT` are the only real failures.** An exception escaping your agent gives `ERROR`; blowing through the whole overage bank gives `TIMEOUT`. In both cases the action for that turn is dropped, the reward is nulled, and the agent is frozen — it is no longer polled, and the replay records default PASS actions for it from then on.

**But a failure is not necessarily fatal to your score.** If your opponent is still alive when the episode reaches its final transition, the interpreter's terminal branch overwrites *every* agent's status to `DONE` and *every* reward to that player's money — including yours. A crash on turn 3 costs you 715 turns of farming but still banks whatever money you had. Verified on 1.32.7: an agent that raises immediately finishes `DONE` with a reward of 3000.0 against a passing opponent.

The exception is mutual failure. If every remaining active agent fails on the same turn, the episode ends there, the terminal branch never runs, and both rewards stay `None`.

Your opponent's failure never touches your reward; you are scored normally either way.

## Agent Contract & Observation Delivery

**Signature.** Your agent is called with `[observation, configuration]` sliced to its declared parameter count: `def agent(obs)` gets the observation, `def agent(obs, config)` gets both. Two traps follow from the slicing being based on the declared count — `def agent(*args)` is called with **zero** arguments, and anything without a `__code__` attribute (a `functools.partial`, a callable class instance, a C builtin) is called with **both**.

**The last callable wins.** A submitted file is executed and the *last callable bound at module level* becomes your agent. A trailing `from math import sqrt` makes `sqrt` your agent; a trailing `class Helper:` makes `Helper` your agent. Keep the agent function as the final definition in the file, and put imports and helper classes above it.

**Loading is lazy.** The module body runs on the first `act()` call, inside that turn's timing window. Heavy imports are charged to turn 0's budget.

**The observation is a `Struct`** — a `dict` subclass that also mirrors its keys onto attributes. `obs["day"]`, `obs.day`, and `obs.get("day", 0)` all work; `obs.get` is the safe form for a key that may be absent, since attribute access raises. It is delivered as plain nested dicts and lists, so it can be deep-copied and mutated freely by a forward model.

**Shared fields come from player 0's copy.** `farms`, `market`, `town`, `day`, `hour` and `step` are declared shared, and the framework delivers them to both agents from the state stored at index 0. `player`, `private` and `remainingOverageTime` are per-agent. This matters when reading replay JSON offline: the `farms`/`market`/`town` stored under player 1 are not what player 1 was shown, and only index 0's copy is authoritative.

**Local agents share a process.** Built-in, callable and file-based agents all run sequentially in the host process, so module-level globals persist across turns — which is how a forward model can cache state between calls — and both agents share that process.

## Built-in Agents

`make("kaggriculture")` registers three opponents, usable by name in `env.run([...])`:

| Name | Behaviour |
| :---- | :---- |
| `pass` | Returns `{"farmer": ["PASS"], "hands": [], "market": []}` every turn. Deterministic; the right baseline for reproducibility tests. |
| `random` | Random movement/water/harvest for every unit, a 10% chance per turn of buying one affordable seed, and a 30% chance of planting a held seed instead of moving. Unseeded. |
| `starter` | A carrot loop: buy a seed when out, plant on the current tile, water until the crop's max-yield age, harvest, sell whatever carrots are in the shed. |

All three take only the observation.

## Determinism & Seeding

`configuration["seed"]` is read once at initialisation, then **set to `None`** and stored as `env.info["seed"]`. Agents therefore never see the seed — it is `None` in the configuration they are handed — but it survives in the replay and across a reset. With no seed supplied, a random 31-bit integer is drawn at `make()` time and used for the whole episode.

All in-episode randomness comes from one generator per day, rebuilt at each end-of-day refresh as `random.Random((seed * 1_000_003) ^ day)`. It is consumed in a fixed order:

1. Player 0's weed rolls, one per tile in row-major order across the whole board.
2. Player 1's weed rolls, the same way.
3. The shop unlock draw, if this day boundary is an unlock day.

Because it is a single shared stream, the two farms do not get the same weeds, and how many tiles player 0 has open changes what player 1 draws. A forward model that rolls weeds per-player independently will diverge from the engine even with the right seed.

Given the same seed and deterministic agents, an episode reproduces exactly, byte for byte. The built-in `random` agent is *not* seeded, so runs against it differ regardless. A replay can also be resumed exactly — reconstruct with `make(..., info=replay["info"], steps=replay["steps"][:k])` and continue; omitting `info` draws a fresh seed and the tail diverges.
