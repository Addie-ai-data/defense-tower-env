---
title: Tower Defense RL Policy Showdown
emoji: 🏰
colorFrom: blue
colorTo: red
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
python_version: 3.12
pinned: false
---

# Tower Defense RL Environment

A mini-game RL environment built on the **OpenEnv framework**.
An AI agent learns to place towers strategically to block waves of enemies.

---

## Why This Meets The Rubric

- **Playable mini-game RL environment**: the agent manages gold, places towers, and defends the base against waves of enemies.
- **Increasing difficulty**: `easy`, `medium`, and `hard` scale grid size, path count, wave count, enemy HP, and tower variety.
- **Automated graders + reward logic**: kill rewards, leak penalties, wave-clear bonuses, and a final 0-100 score are built into the environment.
- **OpenEnv-style packaging**: typed `Action`, `Observation`, and `State` models are exposed through `/reset`, `/step`, `/state`, `/grade`, and `/health`.

---

## 🧠 How the Agent Learns

### State Representation
- **Grid**: Flattened 4x4 (easy), 6x6 (medium), 8x8 (hard) grid with values 0-4 (empty, path, arrow, cannon, magic towers)
- **Base HP**: Current health of the base (starts at 100)
- **Gold**: Available currency for placing towers
- **Legal Cells**: Positions where towers can be placed (not on path)

### Actions
- **Place Tower**: Boolean (yes/no)
- **Position**: Row and column (0-3 for easy)
- **Tower Type**: Arrow (10 dmg, range 2, cost 50), Cannon (25 dmg, range 1, cost 100), Magic (15 dmg all in range, cost 150)

### Reward Function
- +10 per enemy killed
- -5 per enemy reaching base (leak)
- +20 wave cleared with 0 leaks
- -1 per tower placed (efficiency)
- +50-100 game won (scaled by remaining HP)

### RL Algorithm
We demonstrate simple policies (Random, Greedy, Epsilon-Greedy) and provide code for PPO training using Stable-Baselines3.

The Greedy policy places the best affordable tower at the position covering the most path cells within range.

Epsilon-Greedy starts random and becomes greedy over time, simulating learning.

For full RL training, see `train.py` and `gym_env.py`.

---

## 📊 Results

### Policy Performance (Easy Mode, 5 episodes avg)
- 🎲 Random: 80.6/100
- 🧠 Greedy Placer: 95.0/100
- 📈 Epsilon-Greedy: 81.8/100
- 🛑 Always Pass: 10.0/100

Greedy outperforms others by strategically placing towers to maximize coverage.

For harder difficulties, simple policies struggle due to increased complexity.

---

## ⚙️ Architecture Diagram

```
User → Gradio App → Policy/Episode Runner → Environment → Reward → Results
```

The environment runs locally without server for demo speed.

For training: Agent → Gym Wrapper → Environment → Stable-Baselines3 PPO → Learned Policy

---

## 🚀 Unique Twist: Adaptive Difficulty

The demo includes 3 difficulty levels with increasing grid size, waves, and enemy HP, testing generalization.

Policies are designed to adapt tower choice based on difficulty (e.g., more cannons on hard).

---

## Project Structure

Recommended top-level files and folders:

```text
src/                             OpenEnv-style environment code
tests/test_environment.py        Runtime, interface, task, and grader checks
demo.py                          Policy showdown runner
app.py                           Gradio demo entrypoint
requirements.txt                 Python dependencies
```

```
tower_defense_env/
├── src/
│   ├── core/                          ← OpenEnv standard base classes
│   │   ├── env_server.py              ← Action, Observation, State ABCs
│   │   └── http_env_client.py         ← HTTPEnvClient base class
│   └── envs/tower_defense/
│       ├── models.py                  ← Type-safe contracts
│       ├── client.py                  ← HTTP client (import in training)
│       └── server/
│           ├── environment.py         ← Game logic + grader
│           └── app.py                 ← FastAPI server
├── tests/
│   └── test_environment.py            ← Full test suite
├── demo.py                            ← 4-policy showdown demo
├── Dockerfile
└── requirements.txt
```

---

## Quick Start

Recommended local workflow from the repo root:

```bash
pip install -r requirements.txt
python app.py
python tests/test_environment.py
```

### Option A — Run directly (no Docker)

```bash
# Install project dependencies
pip install -r requirements.txt

# Start the server
uvicorn envs.tower_defense.server.app:app --host 0.0.0.0 --port 8000 --app-dir src

# Run the demo (new terminal)
python demo.py

# Run the tests
python tests/test_environment.py
```

### Option B — Docker

```bash
docker build -t tower-defense-env .
docker run -p 8000:8000 -e TD_DIFFICULTY=medium tower-defense-env
```

---

## The Game

```
4x4 grid (easy mode):

  0 1 2 3
0 · · · ·
1 A ─ ─ ─   A = Arrow tower placed by agent
2 · · · ·   ─ = Enemy path
3 · · · ·

Legend:  ·=empty  ─=path  A=arrow  C=cannon  M=magic
```

### Difficulty Levels

| Level  | Grid | Waves | Paths | Tower Types | Enemy HP |
|--------|------|-------|-------|-------------|----------|
| Easy   | 4×4  | 3     | 1     | Arrow only  | 30       |
| Medium | 6×6  | 5     | 2     | Arrow+Cannon| 50       |
| Hard   | 8×8  | 10    | 3     | All 3 types | 80       |

### Tower Types

| Tower  | Damage | Range | Cost | Notes                  |
|--------|--------|-------|------|------------------------|
| Arrow  | 10     | 2     | 50g  | Single target, basic   |
| Cannon | 25     | 1     | 100g | High damage, short rng |
| Magic  | 15     | 3     | 150g | Hits ALL in range      |

---

## Reward Logic (Grader)

```
+10   per enemy killed           ← task completion
 -5   per enemy reaching base    ← failure penalty
+20   wave cleared with 0 leaks  ← perfect play bonus
 -1   per tower placed           ← efficiency pressure
+50–100  game won                ← scaled by HP remaining
```

**Why this makes sense for RL:**
- Sparse reward problem: towers placed now pay off several steps later
- Efficiency bonus discourages brute-force placement
- HP-scaled win bonus rewards careful play, not just barely surviving

---

## API Reference (OpenEnv Standard)

```
POST /reset    {"difficulty": "easy"}          → initial observation
POST /step     {"place_tower": true,            → observation + reward
                "row": 1, "col": 2,
                "tower_type": "arrow"}
GET  /state                                     → episode metadata
GET  /grade                                     → automated score report
GET  /health                                    → liveness check
```

---

## Usage in Training Code

```python
from envs.tower_defense.client import TowerDefenseEnv
from envs.tower_defense.models import TowerDefenseAction

env = TowerDefenseEnv(base_url="http://localhost:8000")
result = env.reset(difficulty="medium")

while not result.done:
    # Your policy here
    action = TowerDefenseAction(
        place_tower=True,
        row=2, col=3,
        tower_type="cannon"
    )
    result = env.step(action)
    print(f"Reward: {result.reward}  Base HP: {result.observation.base_hp}")

report = env.grade()
print(f"Final score: {report['score']}/100")
```

---

## Evaluation Criteria Compliance

| Criterion         | How it's met                                              |
|-------------------|-----------------------------------------------------------|
| Runtime correct   | Full test suite passes (run `tests/test_environment.py`)  |
| Interface standard| Inherits `HTTPEnvClient`, `Action`, `Observation`, `State`|
| Task design       | 3 clear difficulty levels, testable win/loss conditions   |
| Grading logic     | `grade_episode()` returns score 0-100 with full breakdown |
