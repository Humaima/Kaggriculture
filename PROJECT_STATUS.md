# Kaggriculture Agent — Project Status

All 9 phases complete and verified. This documents what was actually built,
tested, and measured in each phase, plus the commands to resubmit.

---

## Current agent summary

- **Architecture**: farmer + up to 9 hired hands (1 weed-patrol, 3
  animal-keepers — cow/sheep/goose, 3 zone-farmers — one per quadrant, 2
  general-duty), each running the same priority-ordered rule-based planner
  (protect assets → harvest → travel → plant → reactive weed cleanup)
  unless diverted to a specialized role
- **Crop selection**: dynamic, ranked by revenue/tile/day (melon typically wins)
- **Selling**: price-curve-aware, capped to avoid crashing our own market
- **Animals**: one dedicated keeper per type (cow, sheep, goose) builds its
  structure, buys/places one animal, and maintains it (feed/care/harvest/
  collect fertilizer) daily, staggered in over the season (Phase 14)
- **Land expansion**: **enabled** (Phase 15) — buys up to all 4 quadrants,
  each worked by a dedicated zone-farmer hand. Re-enabled despite measuring
  as a net loss in every LOCAL self-play test against `starter` (8
  measurements, Phases 9-14) because real leaderboard replays showed a real
  opponent expanding land and profiting from it against us — see Phase 15
  below for the replay evidence
- **Last measured local performance**: land off $31,187, land on (current
  default) $11,168 vs `starter` (seed=42, reproducible) — see Phase 13/14
  for the full 3-seed comparisons and Phase 15 for why land expansion is
  enabled despite the local number being lower
- **Last real Kaggle result**: multiple submissions since `55601687`
  (`55606530`, `55620497`, `55645149`, `55646159`, `55646233` — see `kaggle
  competitions submissions kaggriculture` for the full history and current
  public scores); none of the ones checked had land expansion actually
  active in real matches (`me_land` stuck at 1 for all 720 turns in two
  replays traced directly). Not yet resubmitted with Phase 15's land
  expansion turned on — see "What's next"
- **Known scope limits**: land expansion measured as a net loss in every
  local self-play test (Phases 9-14, 8 measurements) but is enabled anyway
  as of Phase 15 based on real replay evidence that local self-play against
  `starter` doesn't predict real-opponent outcomes here — worth watching
  closely once resubmitted, and reverting if a real submission measures
  worse than the land-off baseline.

---

## Phase-by-phase log

| Phase | What was built | Result |
|---|---|---|
| **1 — Environment Setup** | Python 3.11+ venv, `kaggle-environments`/`kaggle` installed, project structure (`strategy/`, `tests/`, `tools/`) | `main.py` (do-nothing agent) runs a full episode with `status=DONE`, no errors |
| **2 — Explore the Game Data** | `strategy/state.py`: `my_farm`, `tiles_of_kind`, `crop_age`, `needs_water_urgently`, `bfs_path`, `direction_toward` (movement direction convention confirmed empirically, not assumed) | 9/9 unit tests against hand-built `obs` fixtures |
| **3 — Baseline Agent** | `strategy/planner.py` v1: the doc's starter wheat loop, ported to use the Phase 2 helpers | Full 720-turn season: **$3,352 vs `random`** ($0), **$3,333 vs `starter`** ($3,688) — near parity, as expected from matching logic |
| **4 — Encode the Economics** | `strategy/market.py` (price-curve formula), `strategy/crops.py`, `strategy/animals.py` | Price formula validated against **all 9 resources'** documented checkpoints exactly; melon's bonus-window exception correctly modeled; 11 new tests |
| **5 — Build the Planner** | Rewrote `planner.py`: dynamic crop selection, price-aware batch selling, priority-ordered decisions | **$26,688 vs `random`**, **$26,608 vs `starter`** — an **8× improvement** over Phase 3. Caught and fixed a real bug (redundant seed rebuying) via unit tests before it ever ran in an episode |
| **6 — Local Self-Play** | `agents/wheat_loop_v1.py` (standalone frozen snapshot), `tools/self_play.py` (CSV-logged multi-episode harness) | Beat our own Phase 3 predecessor by **+$23,000** in true self-play. Discovered environment-level randomness (`weedSpawnChance`, random shop unlocks) — fixed via `seed=` config for reproducible A/B comparisons |
| **7 — Debug & Refine** | `.vscode/launch.json` debug configs; investigated weed accumulation | Tested 3 variants on the same seed: no handling ($26,688, 9 weeds), proactive chase (**worse**, $25,490), reactive-only (**$26,688**, matches baseline — kept as a free safety net) |
| **8 — Submit & Iterate** | Clean `submission.tar.gz` packaging, extracted-archive testing, Kaggle CLI auth/submit/monitor workflow | **Live submission `55601687`** on the real leaderboard; resolved a corrupted `credentials.json`; learned the rating system is a skill rating (high early volatility), not raw money |
| **9 — Real Match Analysis** | `tools/analyze_replay.py`; diagnosed a real loss via day-by-day trace of replay `94197402` | Found the root cause: board fully saturated (16 plants + 9 weeds = 25 tiles) by day 23, agent flatlines while opponent keeps growing. Implemented and empirically verified `BUY_LAND` syntax, tested twice — **both regressed performance** (single farmer can't cover the extra land fast enough). **Disabled by default**, code kept for a future `HIRE` pairing |

---

## Running the full verification suite

```cmd
cd kaggriculture-agent
.venv\Scripts\activate.bat
python tests\test_strategy_units.py
python tests\test_market.py
python tests\test_crops.py
python tests\test_animals.py
python tests\test_planner.py
python tools\run_match.py
python tools\self_play.py
```
Expect: 68/68 unit tests passing, all harness matchups `DONE` with no `ERROR`. As of Phase 15 (9-hand roster, land expansion ON), `main.py` vs `starter` reproduces **exactly** $11,168 on seed=42 locally — lower than Phase 14's land-off $31,187, deliberately (see Phase 15: shipped based on real replay evidence, not the local number). Neither matches $26,688, the pre-Phase-12 single-farmer baseline kept in the phase log below for historical comparison.

---

## What's next (not yet done)

1. **Resubmit to Kaggle with Phase 15's land expansion on** — the highest-priority item now. Every submission checked so far (`55601687` through `55645149`/`55646233`) had land expansion off; this would be the first real test of Phase 15's decision to enable it based on replay evidence rather than the local measurement. Watch the resulting replays with `tools/analyze_replay.py` the same way Phase 15 diagnosed the problem, and compare the public/private score against the pre-Phase-15 submissions (see `kaggle competitions submissions kaggriculture` for the history).
2. **If Phase 15 doesn't pan out**: revert `ENABLE_LAND_EXPANSION` to `False` in `strategy/planner.py` — that configuration is still fully supported and unit-tested, just no longer the default. The local numbers ($31,187/$30,723/$31,445 vs `starter`) are unchanged and remain the fallback.
3. **Fertilizing** — `FERTILIZE` is fully documented and modeled in `crops.py`'s bonus windows, but the planner never calls it. Doubles the per-day yield bonus during a crop's bonus window.
4. **End-of-season liquidation** — near day 28–30, the planner should bypass its price-floor sell throttle, since there's no future price left to protect.

---

## Resubmitting to Kaggle

**Note:** the current `main.py` behaves identically to submission `55601687` (the Phase 9 land-expansion code is implemented but disabled, so it's a no-op). There's nothing functionally new to submit until one of the "what's next" items above is implemented — resubmitting now would just spend a daily slot on an unchanged agent. Once you do have a real change:

### 1. Activate the venv
```cmd
cd C:\Users\Lenovo\Downloads\kaggriculture-agent
.venv\Scripts\activate.bat
```

### 2. Run the full test suite (don't submit on a red build)
```cmd
python tests\test_strategy_units.py
python tests\test_market.py
python tests\test_crops.py
python tests\test_planner.py
```

### 3. Measure the change locally first, on the same seed used throughout this project
```cmd
python -c "from kaggle_environments import make; env = make('kaggriculture', configuration={'episodeSteps': 720, 'seed': 42}, debug=True); env.run(['main.py', 'starter']); final = env.steps[-1]; print(final[0].reward, final[1].reward)"
```
Compare against the **$26,688** baseline — only proceed to submit if this is a real, measured improvement.

### 4. Clean and package
```cmd
for /d /r %d in (__pycache__) do @if exist "%d" rd /s /q "%d"
tar -czf submission.tar.gz main.py strategy
tar -tzf submission.tar.gz
```

### 5. Test the extracted archive from a clean directory
```cmd
if exist "%TEMP%\submission_test" rmdir /s /q "%TEMP%\submission_test"
mkdir "%TEMP%\submission_test"
cd /d "%TEMP%\submission_test"
tar -xzf "C:\Users\Lenovo\Downloads\kaggriculture-agent\submission.tar.gz"
python -c "from kaggle_environments import make; env = make('kaggriculture', configuration={'episodeSteps': 48}, debug=True); env.run(['main.py', 'random']); final = env.steps[-1]; [print(f'Player {i}: reward={s.reward}, status={s.status}') for i, s in enumerate(final)]"
cd /d C:\Users\Lenovo\Downloads\kaggriculture-agent
```
Expect: both `status=DONE`, no import errors.

### 6. Submit
```cmd
kaggle competitions submit kaggriculture -f submission.tar.gz -m "Describe what changed here"
```

### 7. Monitor
```cmd
kaggle competitions submissions kaggriculture
kaggle competitions episodes SUBMISSION_ID
kaggle competitions replay EPISODE_ID -p .\replays
kaggle competitions logs EPISODE_ID 0 -p .\logs
kaggle competitions leaderboard kaggriculture -s
```
(Replace `SUBMISSION_ID`/`EPISODE_ID` with real numbers from the previous command's output.)

### 8. Analyze the result
```cmd
python tools\analyze_replay.py replays\<episode-file>.json
```
This traces money/plants/weeds day-by-day for both players — the same method that diagnosed the land-ceiling problem in Phase 9.

**Reminder:** once submitted, your agent keeps playing episodes automatically for the rest of the competition — you don't need to resubmit to "keep it alive." The 5/day limit caps how many *different versions* you can try, not how often you must submit. Only your latest 2 submissions count toward the final leaderboard.

---

## Phase 10 & 11 — Hands, Land, Role Specialization (Investigated, disabled by default)

Built full `HIRE`, `BUY_LAND`, and multi-unit coordination (mechanically correct, confirmed empirically, 32/32 unit tests passing). Tested 7 distinct configurations across 3 seeds each (21 measurements total):

| Configuration | vs `starter`, avg across 3 seeds |
|---|---|
| **Baseline (single farmer, current default)** | **~$26,660** |
| 3 hands + 3 quadrants (uncapped) | ~$22,100 |
| 2 hands + 2 quadrants (capped) | ~$23,240 |
| 1 dedicated weed-patrol hand, no land | ~$26,400 (weeds: 9 → **0**) |
| 1 weed-patrol hand + land | ~$25,130 |

**Every configuration involving land expansion lost money.** The one configuration involving hands alone (no land) came close to breakeven and fully solved the weed problem, but still didn't beat doing nothing. The mechanism is sound (no bugs — no double-planting, correct seed-quantity scaling, no duplicate travel targets), but our current coordination logic isn't sophisticated enough to convert the extra land/labor into more profit than a simpler, focused strategy.

**Both `ENABLE_LAND_EXPANSION` and `ENABLE_HIRING` are off by default** (`strategy/planner.py`) — this reflects the same discipline used throughout the project: never ship a measured regression, even when the feature "sounds like it should help." Real-world leaderboard performance is not guaranteed to match local self-play against `starter`, so this remains worth revisiting with real match data.

**Best next lever, not yet tried**: `FERTILIZE` — fully modeled in `crops.py`'s bonus windows, never wired into the planner. Unlike land/hands, it doesn't introduce multi-unit coordination overhead, making it a lower-risk next experiment.

---

## Phase 12 — Animal Husbandry (Enabled — first configuration to beat baseline!)

A real leaderboard screenshot (day-30 view of two strong players) showed both running cows and sheep at meaningful scale, plus multiple hands. Confirmed the full mechanical pipeline empirically before writing any code: `BUY_ANIMAL`/`BUY_PRODUCT` land in the **shed** (not directly in inventory, unlike seeds), so a unit must `PICKUP` from a shed-adjacent tile before it can `PLACE` an animal or `FEED` one. The farmer's spawn tile `(4,4)` is shed-adjacent — confirmed live.

**Real bug found and fixed via live tracing**: the animal-keeper hand only fed "when urgently needed" (`needs_feed_urgently()`, which correctly implements the doc's grace period), but that let it wander off on weed-patrol duty right when it mattered — the fetch-wheat-and-return cycle took longer than the grace period allowed, and the first cow tested escaped from starvation. Fixed by feeding on the *first* opportunity each day and never falling back to weed patrol while any animal is unfed.

**Result — the first configuration in Phases 9–12 to beat the baseline:**

| Seed | Baseline | + weed-patrol + animal-keeper hands |
|---|---|---|
| 42 | $26,688 | **$28,745** (+7.7%) |
| 7 | $26,608 | **$29,255** (+9.9%) |
| 99 | $26,688 | **$29,673** (+11.2%) |

`ENABLE_HIRING` and `ENABLE_ANIMALS` are now **enabled by default** in `strategy/planner.py`. The agent now runs 2 hired hands daily: one dedicated weed-patrol hand (Phase 11), and one dedicated animal-keeper hand that builds a pasture, buys and places one cow, and maintains it (feed/care/harvest/collect fertilizer) every day. 57/57 unit tests pass with these as the real defaults; the submission tarball was tested from a clean directory and runs without errors.

**Known caveat**: one early escape happened in the seed=42 trace (day 5, before the proactive-feeding fix had been proven live) — a replacement cow was placed and stayed healthy from day 12 onward. Worth monitoring on real leaderboard matches, where opponent behavior and timing may differ from `starter`.

---

## Phase 13 — Animal Diversification + Full Hand Roster (Enabled — biggest win yet); Zone-Based Land Expansion (Tried Twice More, Still Off — Real Root Cause Found)

Prompted by feedback that the farm wasn't expanding into new land or growing animals beyond a single cow, and a follow-up request to build *real* per-quadrant coordination rather than just more undifferentiated labor. Four rounds of changes, each measured before the next was built on top of it:

**Round 1 — animal diversification + more hands, land still off:**

1. **One animal-keeper hand per animal type** (was: one keeper, cow only). `_decide_animal_keeper_action` took on a `desired_animal` parameter — cow, sheep, and goose keepers each build their own structure (pasture for cow/sheep, coop for goose — fixed a real bug where `BUILD_PASTURE` was hardcoded for every animal, which would have been wrong for goose), buy/place their own animal, and maintain it. Cow- and sheep-keepers share `PASTURE` as a structure kind, so the shared `claimed` set (already used for travel-target dedup) now also stops them targeting the same empty pasture — verified directly against `_decide_animal_keeper_action` in `test_sheep_keeper_does_not_target_the_pasture_the_cow_keeper_already_claimed`.
2. **`MAX_HANDS_PER_DAY` raised 2 → 6** (1 weed-patrol + 3 animal-keepers + 2 general-duty hands, the last of which run the same priority list as the farmer — plant/water/harvest — rather than sit idle).
3. **`ENABLE_LAND_EXPANSION` re-tried a 4th time** (previously lost in Phases 9, 10, 11) — still lost, both fully uncapped (4 quadrants, -20.1%) and capped at 2 (-8.6%), confirming labor coverage alone doesn't fix it. Disabled again.

The 6-hand, land-off roster measured a real win: $28,779 / $28,270 / $29,291 (seeds 42/7/99) vs the $26,688 / $26,608 / $26,688 baseline (+6-10%).

**Round 2 — real zone-based coordination for land expansion**, on the theory that Phases 9-11's losses were a coordination problem (all hands chasing the same nearest-target board-wide) rather than a labor-shortage problem:

4. Added `strategy.state.quadrant_of(x, y, board_size)`, matching the engine's own convention exactly (confirmed by reading the installed `kaggle_environments` package source, not assumed).
5. `_decide_unit_action` took on a `zone` parameter that restricts its thirsty/harvestable/empty-tile searches to one quadrant.
6. The farmer is zone-restricted to `NW` (its spawn quadrant); 3 new **zone-farmer** hands are each assigned one of `ZONE_ORDER = ["NE", "SW", "SE"]` — the engine's actual land-purchase order, confirmed via `kaggriculture.py`'s `LAND_ORDER` — so a newly bought quadrant gets its own dedicated worker instead of competing for attention. A zone-farmer falls back to farm-wide duty if its quadrant isn't unlocked yet.
7. Along the way, found and fixed two real bugs unrelated to zoning itself:
   - **Market-order priority**: `SELL` orders were queued *before* `HIRE`/`BUY_LAND`, and the engine silently drops orders past `maxMarketOrdersPerTurn` (default 10) — a shed with several sellable resources could push the time-sensitive HIRE/BUY_LAND orders off the end with no warning. Reordered to queue HIRE/BUY_LAND/BUY_SEED/BUY_ANIMAL/BUY_PRODUCT first, SELL last and explicitly trimmed to the remaining room (`MAX_MARKET_ORDERS_PER_TURN`).
   - **Cross-category budget double-counting**: HIRE, BUY_LAND, BUY_SEED, BUY_ANIMAL, and BUY_PRODUCT each independently checked their own cash-reserve gate against the *same* undiminished `me["money"]`, so several categories could each individually look affordable in the same turn while cumulatively overspending once the engine processed them in sequence. Fixed with a single running `available_cash` in `decide()`, decremented as each category commits spend.
8. The market-order fix alone, independent of anything land-related, improved the Round-1 land-off baseline further: **$31,187 / $30,723 / $31,445** (seeds 42/7/99) vs the original $26,688/$26,608/$26,688 baseline (+16-18%). This is the number now shipped.
9. But the full zone-farmer configuration (9 hands, land expansion on) still measured catastrophically worse: **$4,233 / $4,383 / $4,337** — barely above `starter`'s own number, not a modest regression like Phases 9-11's ~9-20% losses.

**Round 3 — root-cause diagnosis**, via day-by-day money/hand-count traces (`tools/analyze_replay.py`-style, not guessing): the zone-coordination logic itself works correctly — each quadrant reliably gets its own worker, confirmed via unit tests. The real cause is an **onboarding-pace problem**: scaling from 0 to 9 hands in a single day-0 burst, combined with 3 simultaneous `BUY_ANIMAL` orders and per-turn seed demand from ~6 units competing over one 5x5 quadrant (land isn't unlocked yet that early), bleeds the $3,000 starting cash down to under $20 by the end of day 0 — before any harvest income arrives. That drops below `HIRE_CASH_RESERVE`, blocking rehiring, and the farm falls into a recurring boom-bust cycle for the rest of the season (hire 9 → crash the bank → forced back to 0 hands → slowly recover via harvests → hire 9 again → crash again) that never compounds steadily. This is a genuinely different problem from every prior land-expansion loss, and wasn't fixed here — see "What's next."

| Configuration | seed=42 | seed=7 | seed=99 |
|---|---|---|---|
| Baseline (no hands, land off) | $26,688 | $26,608 | $26,688 |
| 6-hand roster, land off (Round 1) | $28,779 (+7.8%) | $28,270 (+6.2%) | $29,291 (+9.8%) |
| **6-hand roster, land off, market-order fix (shipped)** | **$31,187** (+16.9%) | **$30,723** (+15.5%) | **$31,445** (+17.8%) |
| 9-hand zone-farmer roster, land ON | $4,233 (-84.1%) | $4,383 (-83.5%) | $4,337 (-83.7%) |

`ENABLE_LAND_EXPANSION` stays off; `MAX_QUADRANTS_TO_BUY` stays at the full 4 quadrants (harmless while the flag is off, ready for a future attempt) and `ZONE_ORDER`/zone-restriction code stays in place as real, unit-tested infrastructure — it's the onboarding pace, not the coordination logic, that needs fixing next. **The animal diversification, larger hand roster, and both bug fixes are a clear, reproducible win on their own** (measured on all 3 established seeds) and are enabled by default.

**Not yet resubmitted to the real Kaggle leaderboard** with this change — see "What's next" below before spending a daily submission slot on it.

---

## Phase 14 — Staggered Onboarding (Fixes Phase 13's Root Cause, Land Expansion Still Off)

Direct follow-up to Phase 13's diagnosis: the zone-coordination logic worked, but scaling to 9 hands + 3 animals in a single day-0 burst overwhelmed the $3,000 starting cash before any income arrived, triggering a boom-bust hire/crash cycle. This phase fixes the pacing, not the coordination:

1. **`HAND_RAMP_START` + `_hand_ramp_cap(day)`** — hiring ramps from `HAND_RAMP_START` hands on day 0 by +1/day, instead of jumping straight to the full roster. **Gated by `ENABLE_LAND_EXPANSION`**: measured applying the ramp with land off too, and it was a pure cost (-6.3%, $29,222 vs $31,187) since the proven land-off roster never had a day-0 cash crash to fix in the first place.
2. **`ANIMAL_KEEPER_STAGGER_DAYS`** — each animal-keeper role (cow, sheep, goose) only activates once the season reaches `keeper_slot * ANIMAL_KEEPER_STAGGER_DAYS`; before that, the hand patrols weeds instead of immediately buying its animal. Also gated by `ENABLE_LAND_EXPANSION` for the same reason.
3. Along the way, converted `MAX_HANDS_PER_DAY` from a frozen module constant into `_max_hands_per_day()`, a function — the constant was computed once at import time from `ENABLE_LAND_EXPANSION`'s value then, so runtime toggles (tests, or any future dynamic use) silently saw a stale number.
4. Tried delaying the *first* (cow) keeper's activation too (shifting the stagger formula so even slot 0 waits) — measured **worse** ($7,940 vs $11,168 on seed=42), since cow is the highest-revenue animal and delaying it cost more in lost production than the cash-crash relief was worth. Reverted; cow keeper still activates immediately (slot 0 = day 0).
5. Tried `HAND_RAMP_START=2` first, then `=1` — `=1` measured marginally better across all 3 seeds and is what's shipped.

**Result — the boom-bust collapse is fixed** (confirmed via day-by-day trace): money holds flat instead of crashing further during the pre-harvest wait, then recovers into steady growth, unlocking all 4 quadrants by day ~22. But it's still a clear net loss vs the land-off default:

| Configuration | seed=42 | seed=7 | seed=99 |
|---|---|---|---|
| 6-hand roster, land off (shipped) | $31,187 | $30,723 | $31,445 |
| 9-hand zone-farmer roster, land ON, **no staggering** (Phase 13) | $4,233 | $4,383 | $4,337 |
| 9-hand zone-farmer roster, land ON, **staggered** (Phase 14, `HAND_RAMP_START=2`) | $10,920 | $10,081 | $9,819 |
| 9-hand zone-farmer roster, land ON, **staggered** (Phase 14, `HAND_RAMP_START=1`) | $11,168 | $11,686 | $12,446 |

~2.7x better than Phase 13's collapse, but still -60% to -64% vs land off. This was the 8th separate land-expansion measurement across Phases 9, 10, 11, 13 (x2), and 14 (x3 seeds) to lose money locally, and at the time `ENABLE_LAND_EXPANSION` was kept off as a result — the underlying economics (9 hands' overhead plus a multi-day recovery wait) didn't seem to pay for themselves within a 30-day season under this agent's coordination style, at least against the scripted `starter` bot. **See Phase 15 immediately below: this conclusion was reversed days later, based on real leaderboard replay evidence rather than another local measurement.**

---

## Phase 15 — Re-enabled Land Expansion Based on Real Replay Evidence (Overrides Phase 9-14's Local Finding)

Prompted by a user report ("tiles are only in one block, most of the area remains grey and untouched") plus a screenshot of a real leaderboard match showing an opponent with a much larger, actively-farmed area. Rather than diagnose from the screenshot alone, pulled real replay data: `kaggle competitions submissions kaggriculture` turned up several submissions made in earlier, untracked sessions (`55606530` "Buy Lands, and other functions added for the agent", `55620497` reaching $33,012 locally, `55645149` "Phase 12" hands) that this project's own docs had no record of. Downloaded and traced two of their actual replays with `tools/analyze_replay.py`:

| Episode | Submission | Day 29: our money (our land) | Day 29: opponent money (opponent land) |
|---|---|---|---|
| 95098360 | `55606530` | $13,994 (1) | $14,724 (2) |
| 95029677 | `55620497` | $14,218 (1) | **$28,399** (2) |

In **both** real matches, our agent's `me_land` stayed at exactly 1 for all 720 turns — `ENABLE_LAND_EXPANSION` was off in those historical submissions too, consistent with every phase's local finding. But the **real opponent** expanded to 2 quadrants around day 17-19 in both matches and, in the second, nearly doubled us by day 29. This directly confirms the caveat this project's docs have carried since Phase 8: *"the rating system... real-world leaderboard performance is not guaranteed to match local self-play against `starter`."* Now there's a concrete data point showing it doesn't, in the direction that matters: a real opponent profits from land expansion against us even though expansion measured as a net loss in 8 separate local self-play tests (Phases 9-14) against the scripted `starter` bot.

**Decision**: re-enable `ENABLE_LAND_EXPANSION` despite the local number being lower ($11,168 vs $31,187 on seed=42), specifically to test it against real opponents rather than trust local self-play as the final word here. Phase 14's zone-farmer + staggered-onboarding infrastructure is kept in place under this change (it already fixed the worst local failure mode, the day-0 cash crash), so this isn't a return to Phase 9-11's naive, undifferentiated version. 68/68 unit tests pass (3 tests that had implicitly relied on `ENABLE_LAND_EXPANSION`'s old default of `False` were updated to pin it explicitly, since that configuration is still fully supported, just no longer the default).

**This is a real, live experiment, not a proven win** — unlike every other change in this log, it's shipped *despite* a worse local measurement, on the strength of limited real-match evidence (2 replays, not a controlled A/B test). Revert to `False` if a real submission with this on measures worse than the land-off baseline on the public/private leaderboard score.
