# Kaggriculture — Complete Project Guide (VS Code Edition)

A phase-by-phase plan for building, testing, and submitting an agent for the [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) competition, set up to run entirely in Visual Studio Code.

---

## 0. The Game in One Page (mental model before you code)

You control a **farmer** (+ optional hired **hands**) on a 10×10 grid split into four 5×5 quadrants. You start owning only the NW quadrant. The season is **720 turns** (24 turns/day × 30 days). One action per unit per turn. Whoever has the most **money** at turn 720 wins.

Core loop every turn:
1. Move / act with farmer (and each hired hand).
2. Queue up to 10 market orders (`BUY_SEED`, `BUY_ANIMAL`, `BUY_PRODUCT`, `SELL`, `HIRE`, `BUY_LAND`).
3. Engine resolves actions → market → town consumption → day refresh (if hour wraps) → prices update.

Key subsystems you'll need to model in code:
- **Crops**: one-time (wheat, carrot, melon) vs. ongoing (tomato, strawberry) yield curves, watering/fertilizing bonuses, weed risk if unwatered 2 days running.
- **Animals**: goose/coop, cow/pasture, sheep/pasture — feeding, care bonus banking, fertilizer collection, escape risk if unfed 2 days.
- **Shed/inventory**: 100-item cap, end-of-day auto-drop from farmer/hands.
- **Market**: dynamic price curve per resource (scarcity vs. glut, different curve shapes per resource — see the pricing table in the competition doc), town shops/town center draining supply over time.
- **Expansion**: buying land ($1k/$2k/$4k) and hiring hands (Fibonacci-cost per extra hire per day).

Your agent is a pure function: `agent(obs) -> {"farmer": [...], "hands": [[...], ...], "market": [[...], ...]}`. No hidden state is provided by the platform between calls unless you persist it yourself (module-level globals work since the process stays alive for the whole episode).

---

## 1. Set Up Your Local Environment in VS Code

### 1.1 Python version

Kaggle's `kaggle-environments` package now requires **Python ≥ 3.11** (confirmed on PyPI, current release 1.32.2). Use **Python 3.11 or 3.12** locally — both are fully compatible with `kaggle-environments`, `pygame` (if you add a custom visualizer), `numpy`, `gymnasium`, and the other dependencies pulled in transitively. Avoid 3.9/3.10 (too old for the package) and be cautious with 3.13+ until you've confirmed `pygame`/`stable-baselines3` wheels exist for it on your OS.

| Package | Minimum compatible Python | Notes |
|---|---|---|
| `kaggle-environments` | **3.11+** (hard requirement) | Pulls in `gymnasium`, `pettingzoo`, `stable-baselines3`, `scipy`, `Flask` |
| `pygame` | 2.7+ works on 3.8–3.13 | Only needed if you build your own local visualizer/replay viewer |
| `kaggle` (CLI) | 3.8+ | For submission/monitoring |
| `numpy`, `scipy` | 3.11 fine | Installed automatically as deps |

**Recommendation:** target **Python 3.11.x** as your project's interpreter — it's the safest intersection of "meets kaggle-environments' floor" and "everything else has mature wheels."

### 1.2 Install Python 3.11 (if you don't have it)

- **Windows**: install from python.org (check "Add to PATH"), or `winget install Python.Python.3.11`
- **macOS**: `brew install python@3.11`
- **Linux**: `sudo apt install python3.11 python3.11-venv` (or use `pyenv install 3.11.9`)

### 1.3 VS Code setup

1. Install the **Python** extension (Microsoft) and **Pylance** from the VS Code Extensions panel.
2. Open a new empty folder for the project, e.g. `kaggriculture-agent/`, via `File > Open Folder`.
3. Open the integrated terminal (`` Ctrl+` ``) and create a virtual environment pinned to 3.11:

```bash
python3.11 -m venv .venv
```

4. Activate it:
   - macOS/Linux: `source .venv/bin/activate`
   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
5. In VS Code, open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) → **Python: Select Interpreter** → choose `.venv` (it should read Python 3.11.x).
6. Confirm the terminal prompt shows `(.venv)` before installing anything.

### 1.4 Install dependencies

```bash
pip install -U pip
pip install -U kaggle-environments kaggle
pip install pygame          # optional, only if you build a custom local visualizer
pip install numpy pandas    # optional, useful for strategy/backtesting analysis
```

Verify:

```bash
python -c "import kaggle_environments; print(kaggle_environments.__version__)"
```

---

## 2. Project Structure

Create this layout inside your VS Code folder:

```
kaggriculture-agent/
├── .venv/                     # virtual env (add to .gitignore)
├── .vscode/
│   ├── launch.json             # debug configs
│   └── settings.json           # interpreter + linting settings
├── main.py                     # submission entry point — must define agent(obs)
├── strategy/
│   ├── __init__.py
│   ├── state.py                 # parses obs into a friendlier internal state
│   ├── crops.py                  # crop yield/timing math
│   ├── animals.py                # animal care/feed/yield math
│   ├── market.py                  # price-curve helpers, buy/sell decisions
│   └── planner.py                 # top-level decision logic
├── tests/
│   ├── test_local_match.py         # run agent vs random/starter, print results
│   └── test_strategy_units.py      # unit tests for crop/animal math
├── tools/
│   ├── run_match.py                 # CLI script: run N episodes, log outcomes
│   └── visualizer.py                # optional pygame replay viewer
├── replays/                    # saved replay.json files (gitignore if large)
├── requirements.txt
└── README.md
```

Keep `main.py` **thin** — it should just import from `strategy/` and expose `agent(obs)`. This matters because your submission ZIP/tar must have `main.py` at the root and Kaggle unpacks your files into `/kaggle_simulations/agent/`, so all imports must be relative to that root.

`requirements.txt`:
```
kaggle-environments>=1.32.2
kaggle
```
(Don't add `pygame` here if you never import it from `main.py` — it's dev-only and not needed at submission time, keeping your submission size down under the 100 MiB cap.)

---

## 3. Development Workflow — Phase by Phase

### Phase 1 — "Hello Farm": confirm the loop runs

Goal: get *any* valid agent running locally before writing strategy.

`main.py`:
```python
def agent(obs):
    return {"farmer": ["PASS"], "hands": [], "market": []}
```

`tools/run_match.py`:
```python
from kaggle_environments import make

def main():
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
    env.run(["main.py", "random"])
    final = env.steps[-1]
    for i, s in enumerate(final):
        print(f"Player {i}: reward={s.reward}, status={s.status}")

if __name__ == "__main__":
    main()
```

Run it (VS Code terminal, with `.venv` active):
```bash
python tools/run_match.py
```

If this prints two reward/status lines without an `ERROR` status, your environment and file layout are wired correctly. Commit this as your first checkpoint.

### Phase 2 — Understand the observation shape hands-on

Before writing strategy logic, print and inspect `obs` at a few turns so you're working from what the object *actually* looks like, not just the doc:

```python
def agent(obs):
    if obs["hour"] == 0 and obs["day"] in (0, 1, 5):
        import json
        print(json.dumps(obs, indent=2, default=str)[:2000])
    return {"farmer": ["PASS"], "hands": [], "market": []}
```

Confirm you can locate: `obs["private"]["seeds"]`, `obs["private"]["shed"]`, `obs["farms"][obs["player"]]["tiles"]`, `obs["farms"][obs["player"]]["farmer"]`, and `obs["market"]["prices"]`.

### Phase 3 — Port the starter "wheat loop" and get it working end to end

Use the quick-start agent from the competition page as your first real baseline (buy wheat → plant → water → harvest → sell). Move it into `strategy/planner.py` and have `main.py` just call it:

```python
# main.py
from strategy.planner import decide

def agent(obs):
    return decide(obs)
```

Run against `"random"` and `"starter"` (both built-in opponents) and confirm you don't lose money outright:

```python
env.run(["main.py", "starter"])
```

### Phase 4 — Build a state-parsing layer (`strategy/state.py`)

Write helper functions that turn the raw `obs` dict into things you can reason about, e.g.:
- `my_farm(obs)`, `opp_farm(obs)`
- `tiles_of_kind(farm, kind)` → list of (x, y) for PLANT/WEED/empty/coop/pasture
- `nearest(from_xy, targets)` → simple BFS/Manhattan pathing helper (remember: locked tiles are passable, only tile *actions* no-op on them)
- `crop_age(tile, obs)`, `is_in_bonus_window(tile, crop_table)`

This layer is what makes Phase 5+ tractable — write unit tests for it in `tests/test_strategy_units.py` using hand-constructed fake `obs` dicts (no need to run a real episode to test crop-age math).

### Phase 5 — Encode the economics (`strategy/crops.py`, `strategy/animals.py`, `strategy/market.py`)

Hard-code the Object Types and Price Function tables from the competition page as Python constants (dicts keyed by crop/animal/resource name): seed cost, base price, time-to-yield, max yield, bonus-window math, and the per-resource `base/I0/T/below_func/above_func/target` price-curve parameters. This is the highest-leverage phase — most of your edge comes from correctly modeling:
- When watering/fertilizing actually adds yield (bonus windows differ per crop).
- When a plant/animal is about to decay/escape (2-day rule) so you never lose an asset to neglect.
- Rough price impact of a large sell order, so you don't crash your own market by dumping everything at once.

### Phase 6 — Write the planner / decision loop (`strategy/planner.py`)

Start simple and mechanical (a priority-ordered rule list is a perfectly good v1):
1. Water/feed anything close to the 2-day cutoff first (loss-prevention > profit).
2. Harvest anything ready.
3. Sell shed inventory (batch-aware — don't dump everything into a falling price).
4. If money allows, expand (buy seeds/animals, plant/place, eventually hire hands or buy land).
5. Otherwise move toward the next useful tile and `PASS` if nothing to do.

Iterate toward smarter logic (expected-value comparisons between crop types, ROI on hiring a hand for the day, when land expansion pays back) only after the mechanical version is stable and non-negative in local matches.

### Phase 7 — Local test harness & self-play

`tools/run_match.py` → extend into a loop that runs N episodes against `"random"` and `"starter"`, and later against **older saved versions of your own agent** (self-play is the best signal once you're beating the built-ins consistently):

```python
import copy
from kaggle_environments import make

def run_n(agent_path, opponent, n=5, steps=720):
    results = []
    for _ in range(n):
        env = make("kaggriculture", configuration={"episodeSteps": steps})
        env.run([agent_path, opponent])
        final = env.steps[-1]
        results.append([s.reward for s in final])
    return results

if __name__ == "__main__":
    print(run_n("main.py", "starter", n=5))
```

Log results to a CSV so you can track whether each change actually helps before you burn a daily submission slot on Kaggle.

### Phase 8 — Debugging in VS Code

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run local match",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/tools/run_match.py",
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```
Set breakpoints inside `strategy/planner.py`, launch via the Run and Debug panel (`F5`), and step through a real turn's decision-making with the actual `obs` dict in the Variables pane. `"justMyCode": false` matters here because you'll often want to step into `kaggle_environments` itself to see exactly how it validates/consumes your returned action dict.

### Phase 9 — (Optional) Local replay visualizer with pygame

`kaggle-environments` already gives you `env.render(mode="ipython", ...)` for notebooks and `env.toJSON()` for a replay dump, so a custom pygame viewer is *optional* — build it only if you want a faster local debug loop than opening a notebook each time. Skeleton:

```python
# tools/visualizer.py
import json, pygame

def load_replay(path="replays/replay.json"):
    with open(path) as f:
        return json.load(f)

def draw_farm(screen, tiles, origin_x, cell=32):
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            color = (200, 200, 200) if tile is None else (120, 80, 40)
            rect = pygame.Rect(origin_x + x * cell, y * cell, cell - 1, cell - 1)
            pygame.draw.rect(screen, color, rect)

def main():
    pygame.init()
    screen = pygame.display.set_mode((900, 500))
    replay = load_replay()
    step = 0
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                step = min(step + 1, len(replay["steps"]) - 1)
        screen.fill((30, 30, 30))
        farms = replay["steps"][step][0]["observation"]["farms"]
        draw_farm(screen, farms[0]["tiles"], origin_x=0)
        draw_farm(screen, farms[1]["tiles"], origin_x=400)
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()

if __name__ == "__main__":
    main()
```
Generate `replays/replay.json` locally with `json.dump(env.toJSON(), f)` (shown in the competition doc's "Test Locally" section), then step through frames with the arrow key. This is scaffolding, not a requirement — the doc's built-in `env.render(mode="ipython")` is enough for most debugging.

---

## 4. Submitting

### 4.1 Kaggle CLI setup (one-time)

```bash
pip install kaggle
mkdir -p ~/.kaggle
# paste your token from https://www.kaggle.com/settings/api into this file:
nano ~/.kaggle/access_token
chmod 600 ~/.kaggle/access_token
```
Verify: `kaggle competitions list -s "kaggriculture"`

You must also click **"Join Competition"** on the [competition page](https://www.kaggle.com/competitions/kaggriculture) and accept the rules before your first submission will be accepted. Verify with:
```bash
kaggle competitions list --group entered
```

### 4.2 Submit

Single-file:
```bash
kaggle competitions submit kaggriculture -f main.py -m "Wheat loop v1"
```
Multi-file (bundle `strategy/` alongside `main.py`):
```bash
tar -czf submission.tar.gz main.py strategy/
kaggle competitions submit kaggriculture -f submission.tar.gz -m "Rule-based planner v1"
```
Remember: `main.py` must sit at the **root** of the archive, and everything runs from `/kaggle_simulations/agent/` on Kaggle's side — test the exact tar.gz locally by extracting it into a clean temp dir and running it there before submitting, so you catch import-path bugs before burning a submission.

### 4.3 Monitor

```bash
kaggle competitions submissions kaggriculture      # get submission ID + status
kaggle competitions episodes <SUBMISSION_ID>        # once it's played games
kaggle competitions replay <EPISODE_ID> -p ./replays
kaggle competitions logs <EPISODE_ID> 0 -p ./logs   # debug agent errors
kaggle competitions leaderboard kaggriculture -s
```

Limits to keep in mind: 5 submissions/day, only your latest 2 are actively matched/scored, 100 MiB size cap, 8 GiB HDD / 6.5 GiB RAM / 1.6 vCPU at inference time on Kaggle's side — so keep model weights (if any) modest and avoid heavy per-turn computation, since you get one action's worth of compute budget 720 times per episode.

---

## 5. Suggested Iteration Cadence

1. **Day 1–3**: Phases 1–4 — get a running loop, understand `obs`, port the starter agent, build the state-parsing layer.
2. **Day 4–7**: Phases 5–6 — encode crop/animal/market economics, write a rule-based planner that never lets assets decay.
3. **Day 8–10**: Phase 7 — local self-play harness; submit v1–v2 to get real skill-rating signal.
4. **Ongoing**: pull replays/logs for losses, find the specific turn where your agent made a bad call (idle farmer, mistimed sell, missed watering), patch the rule, re-test locally, resubmit. Treat every submission as a data point, not a final answer — the leaderboard needs volume of games to converge, so submit early and often within the 5/day cap rather than perfecting locally for weeks.

---

## 6. Common Pitfalls

- **Forgetting the 2-day watering/feeding rule** — a single missed day is fine, two in a row destroys the asset. This should be your agent's #1 priority check every turn.
- **Selling everything in one giant `SELL` order** — the price walks down unit-by-unit within your own order; large dumps of glut-prone resources (strawberry, melon, milk, wool — all "premium" with steep above-target curves) can crash your own price to the $1 floor.
- **Ignoring locked tiles are passable** — you can path a hand *across* an unbought quadrant, you just can't act on it, which matters for hand routing before you've expanded.
- **Not testing the actual submission artifact** — always extract and run your `.tar.gz` from a clean directory before uploading; import errors that don't show up in your dev folder are the most common cause of a validation-episode `Error` status.
- **Python version mismatch** — if `pip install kaggle-environments` fails with a resolver error, check `python --version` first; anything below 3.11 will fail to resolve the current release.
