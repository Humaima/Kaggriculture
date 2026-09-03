# 🌾 Kaggriculture — Autonomous Farming Agent

An autonomous rule-based farming agent developed for the **Kaggriculture Kaggle competition**, where two players compete over a 30-day farming season to maximize their final bank balance.

The project focuses on **agentic decision-making, environment interaction, economic optimization, multi-agent coordination, and empirical strategy evaluation**.

> **Current status:** Phase 15 complete. The agent currently uses a farmer + specialized farm hands, animal husbandry, dynamic crop selection, market-aware selling, and experimentally enabled land expansion.

---

## 🎯 Competition Overview

Kaggriculture is a farming simulation in which two agents compete to generate the highest possible income.

Each player starts with:

* $3,000
* A single unlocked 5×5 farm quadrant
* A farmer
* Access to seeds, animals, land expansion, hired hands, and a dynamic market

The season lasts **30 days × 24 turns = 720 turns**.

The winner is the player with the greatest amount of money at the end of the season. Unsold inventory does not contribute to the final reward.

The environment includes:

* 🌱 Multiple crops
* 🐄 Livestock
* 👩‍🌾 Hired farm hands
* 🗺️ Expandable land
* 🌿 Random weed growth
* 🏪 Dynamically unlocked shops
* 📈 A dynamic market
* 💰 Price-sensitive selling
* 🧪 Fertilizer and crop bonus windows

---

## 🤖 Agent Architecture

The agent uses a **priority-based rule planner** rather than a trained machine-learning policy.

### High-Level Strategy

Each farmer or hired hand repeatedly evaluates the current environment and selects an action according to a priority hierarchy:

```text
Protect assets
      ↓
Animal care / feeding
      ↓
Harvest
      ↓
Travel toward target
      ↓
Plant
      ↓
Water
      ↓
Reactive weed cleanup
      ↓
PASS
```

Specialized hired hands can be diverted from this general policy to perform dedicated roles.

### Current Roster

The current architecture supports:

* 👩‍🌾 Main farmer
* 🌿 Weed-patrol hand
* 🐄 Cow keeper
* 🐑 Sheep keeper
* 🪿 Goose keeper
* 🌱 Zone-farmer hands
* 🛠️ General-duty hands

The full roster can scale to **9 active units**, with specialized roles assigned according to the current strategy.

---

## 🧠 Core Components

### Dynamic Crop Selection

Rather than planting a fixed crop such as wheat, the planner ranks available crops using their expected economic efficiency.

The strategy considers:

* Seed cost
* Market price
* Yield
* Time to yield
* Tile occupancy
* Expected revenue per tile/day

**Melon typically ranks highly under the current market model.**

---

### 📈 Market-Aware Selling

The Kaggriculture market is dynamic: selling large quantities of a resource increases market inventory and can reduce its future price.

The agent therefore avoids blindly selling everything immediately.

The planner uses:

* Current market price
* Price curves
* Resource-specific behavior
* Selling thresholds
* Batch selling
* Cash requirements

Premium resources are handled particularly carefully because excessive selling can push their prices toward the floor.

---

### 🐄 Animal Husbandry

The agent supports dedicated animal keepers for:

* Cows
* Sheep
* Geese

Each keeper can:

1. Build the required structure
2. Purchase the animal
3. Pick it up from the shed
4. Place it on the appropriate structure
5. Feed it
6. Care for it
7. Harvest its products
8. Collect fertilizer

A live tracing experiment identified and fixed an important feeding failure: waiting until an animal was *urgently* hungry could allow the keeper to waste critical turns on other tasks.

The planner was therefore changed to prioritize animal feeding whenever an animal requires attention.

---

### 🌿 Weed Management

Weeds can occupy otherwise usable farm tiles.

The agent therefore includes:

* Dedicated weed-patrol behavior
* Reactive weed removal
* Weed-aware target selection
* Protection against allowing farm space to become permanently blocked

A dedicated weed-patrol hand reduced observed weeds from **9 to 0** in one controlled experiment, although the additional labor did not initially produce a standalone economic improvement.

---

### 🗺️ Land Expansion

The environment divides the 10×10 board into four 5×5 quadrants:

```text
┌───────────┬───────────┐
│    NW     │    NE     │
│  Farmer   │  Zone 1   │
│           │           │
├───────────┼───────────┤
│    SW     │    SE     │
│  Zone 2   │  Zone 3   │
│           │           │
└───────────┴───────────┘
```

The agent contains explicit quadrant-aware coordination.

Each additional quadrant can be assigned to a dedicated zone farmer rather than allowing all units to compete for the same global targets.

However, land expansion has been highly sensitive to onboarding costs and coordination overhead.

---

## 🔬 Experimental Development

The agent was developed incrementally through controlled experiments rather than adding features without measurement.

### Phase 1 — Environment Setup

Established the Python environment, Kaggle environment, project structure, and initial agent.

**Result:** Full episode execution verified successfully.

### Phase 2 — State Representation

Implemented reusable state utilities including:

* Farm inspection
* Tile filtering
* Crop age calculation
* Urgent watering detection
* BFS pathfinding
* Direction calculation

**Result:** 9/9 unit tests passed.

### Phase 3 — Baseline Agent

Implemented the documented wheat-loop strategy.

**Result:**

| Matchup    |  Agent |
| ---------- | -----: |
| vs Random  | $3,352 |
| vs Starter | $3,333 |

This established the baseline for subsequent experiments.

### Phase 4 — Economic Modeling

Implemented:

* Market price calculations
* Crop economics
* Animal economics

The market-price implementation was validated against all documented resource checkpoints.

### Phase 5 — Dynamic Planner

Replaced the simple wheat loop with:

* Dynamic crop selection
* Price-aware selling
* Priority-based planning

**Result:** approximately **$26.6K**, representing an approximately **8× improvement** over the original baseline.

A redundant seed-purchasing bug was also identified and fixed through unit testing.

### Phase 6 — Local Self-Play

Built a reproducible self-play harness with CSV logging.

This exposed environmental randomness such as:

* Weed spawning
* Random shop unlocking

Deterministic seeds were subsequently used for controlled A/B experiments.

### Phase 7 — Debugging & Refinement

Investigated weed accumulation and tested:

* No weed handling
* Proactive weed chasing
* Reactive weed cleanup

Proactive weed chasing reduced economic performance, so reactive cleanup was retained as a safety mechanism.

### Phase 8 — Kaggle Submission Pipeline

Implemented:

* Submission packaging
* Clean archive testing
* Kaggle CLI submission
* Submission monitoring
* Replay downloading
* Replay analysis

A real Kaggle submission was successfully executed.

### Phase 9 — Real Match Analysis

Replay analysis revealed a major failure mode:

> The farm could become saturated with plants and weeds, causing the agent to stop generating additional income while an opponent continued expanding.

This led to investigation of land expansion.

### Phases 10–14 — Hands, Land & Animals

Several multi-unit configurations were evaluated.

The experiments showed that simply adding labor or land was not enough.

A major discovery was that hiring too many hands and buying animals too quickly could consume the initial **$3,000** before the first harvest, producing a boom-bust cycle.

A staggered onboarding strategy was subsequently implemented.

### Phase 15 — Real-World Replay Evidence

Local self-play repeatedly suggested that land expansion was economically unfavorable.

However, analysis of real Kaggle replays showed opponents successfully expanding their farms while outperforming the agent.

Two real replays were examined:

| Episode  | Our Land | Opponent Land | Our Money | Opponent Money |
| -------- | -------: | ------------: | --------: | -------------: |
| 95098360 |        1 |             2 |   $13,994 |        $14,724 |
| 95029677 |        1 |             2 |   $14,218 |    **$28,399** |

Based on this evidence, land expansion was re-enabled as a **live leaderboard experiment**, despite its weaker local self-play score.

This is intentionally treated as an experiment rather than a proven improvement.

---

## 📊 Key Experimental Results

The strongest measured land-off configuration achieved:

| Seed | Baseline | Best Land-Off Agent | Improvement |
| ---: | -------: | ------------------: | ----------: |
|   42 |  $26,688 |         **$31,187** |      +16.9% |
|    7 |  $26,608 |         **$30,723** |      +15.5% |
|   99 |  $26,688 |         **$31,445** |      +17.8% |

The major improvement came from combining:

* Specialized farm hands
* Animal diversification
* Better market-order prioritization
* Shared cash-budget accounting
* Dynamic planning

The market-order fix was particularly important because Kaggriculture silently drops market orders beyond the per-turn limit.

---

## 🧪 Testing

The project contains a unit-test suite covering:

* State utilities
* Market calculations
* Crop logic
* Animal behavior
* Planner behavior

Run the complete verification suite with:

```bash
python tests/test_strategy_units.py
python tests/test_market.py
python tests/test_crops.py
python tests/test_animals.py
python tests/test_planner.py
```

The latest project status reports:

**68/68 unit tests passing.**

The project also includes local match and self-play testing:

```bash
python tools/run_match.py
python tools/self_play.py
```

---

## 📁 Repository Structure

```text
kaggriculture-agent/
│
├── main.py
│
├── strategy/
│   ├── state.py
│   ├── planner.py
│   ├── market.py
│   ├── crops.py
│   └── animals.py
│
├── agents/
│   └── wheat_loop_v1.py
│
├── tests/
│   ├── test_strategy_units.py
│   ├── test_market.py
│   ├── test_crops.py
│   ├── test_animals.py
│   └── test_planner.py
│
├── tools/
│   ├── run_match.py
│   ├── self_play.py
│   └── analyze_replay.py
│
├── README.md
├── PROJECT_STATUS.md
└── submission.tar.gz
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <YOUR-REPOSITORY-URL>
cd kaggriculture-agent
```

### 2. Create the virtual environment

```bash
python -m venv .venv
```

### 3. Activate it

**Windows:**

```cmd
.venv\Scripts\activate
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install kaggle-environments kaggle
```

### 5. Run the agent

```bash
python main.py
```

### 6. Run the tests

```bash
python tests/test_strategy_units.py
python tests/test_market.py
python tests/test_crops.py
python tests/test_animals.py
python tests/test_planner.py
```

---

## 🏆 Kaggle Submission

Create a clean submission archive containing the agent and strategy modules:

```cmd
tar -czf submission.tar.gz main.py strategy
```

Verify the archive:

```cmd
tar -tzf submission.tar.gz
```

Submit using the Kaggle CLI:

```cmd
kaggle competitions submit kaggriculture \
    -f submission.tar.gz \
    -m "Describe what changed"
```

Monitor submissions:

```cmd
kaggle competitions submissions kaggriculture
```

Inspect competition episodes:

```cmd
kaggle competitions episodes kaggriculture
```

Download replays:

```cmd
kaggle competitions replay EPISODE_ID -p .\replays
```

Analyze a replay:

```cmd
python tools/analyze_replay.py replays\<episode-file>.json
```

---

## 🔍 Reproducibility

Controlled experiments use deterministic environment seeds where possible.

The primary comparison seeds used throughout development are:

```text
42
7
99
```

For example:

```python
from kaggle_environments import make

env = make(
    "kaggriculture",
    configuration={
        "episodeSteps": 720,
        "seed": 42
    },
    debug=True
)

env.run(["main.py", "starter"])
```

This allows strategy changes to be compared against the same environment conditions.

---

## 🧩 Design Principles

The development of this agent follows several principles:

### Measure before optimizing

New mechanisms are tested against reproducible baselines rather than assumed to improve performance.

### Prefer simple strategies when complexity does not pay

Several experiments showed that additional hands and land can introduce coordination and economic overhead.

### Use real replays to challenge local assumptions

Local self-play against `starter` is useful for controlled experimentation, but real leaderboard opponents can behave differently.

### Fix infrastructure-level problems before adding intelligence

Examples include:

* Market-order limits
* Budget double-counting
* Incorrect animal structure selection
* Animal feeding timing
* Duplicate target assignment

### Keep failed experiments

Regressions are retained in the project history because they document *why* certain mechanisms were disabled and provide useful baselines for future experimentation.

---

## 🔮 Future Work

The current project identifies several promising improvements:

* 🧪 Integrate **FERTILIZE** into the planner
* 💰 Implement end-of-season liquidation logic
* 🗺️ Further optimize land-expansion economics
* 👩‍🌾 Improve multi-hand coordination
* 📊 Perform more real-replay analysis
* 🧠 Replace selected heuristics with learned or adaptive policies
* 📈 Develop stronger opponent-aware strategy selection
* 🔄 Automatically compare strategy variants across fixed seeds

The highest-priority experiments are those that improve economic return **without introducing excessive coordination overhead**.

---

## 📚 Project Documentation

For a detailed development history, experiment log, measured results, and current implementation status, see:

**[`PROJECT_STATUS.md`](PROJECT_STATUS.md)**

The original Kaggriculture environment specification is also preserved in the repository documentation.

---

## 🛠️ Technologies

* **Python**
* **Kaggle Environments**
* **Kaggle CLI**
* Rule-based planning
* BFS pathfinding
* Economic modeling
* Deterministic simulation
* Self-play evaluation
* Replay analysis
* Unit testing

---

## 📌 Project Status

**Status:** 🟢 Active / Experimental

**Current phase:** Phase 15

**Unit tests:** 68/68 passing

**Best measured land-off result:** ~$31.4K

**Current strategy:** Specialized hands + animal husbandry + market-aware planning + experimentally enabled land expansion

> Land expansion is currently a **live experiment**, not a confirmed improvement. Local self-play favors the land-off strategy, while real Kaggle replay evidence provides motivation to test expansion against actual opponents.

---

## 👩‍💻 Author

**Humaima Anwar**

MS Artificial Intelligence
Computer Engineering Background

This project was developed as an exploration of **autonomous agents, decision-making, simulation-based optimization, and practical AI engineering** through competitive Kaggle experimentation.
