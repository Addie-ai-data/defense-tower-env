"""
Tower Defense RL — FastAPI Server

Endpoints:
  POST /reset       → start new episode
  POST /step        → take an action
  GET  /state       → get episode metadata
  GET  /grade       → get automated grading report
  GET  /health      → liveness check

Run with:
  uvicorn envs.tower_defense.server.app:app --host 0.0.0.0 --port 8000
"""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from envs.tower_defense.models import TowerDefenseAction
from envs.tower_defense.server.environment import TowerDefenseEnvironment

app = FastAPI(
    title="Tower Defense RL Environment",
    description="OpenEnv-compliant mini-game environment for RL training.",
    version="1.0.0",
)

# One global environment instance (single-agent, single-episode at a time)
env = TowerDefenseEnvironment()


# ------------------------------------------------------------------ #
# Pydantic request models (for FastAPI validation)                    #
# ------------------------------------------------------------------ #

class ResetRequest(BaseModel):
    difficulty: str = Field(
        default="easy",
        description="Game difficulty: 'easy', 'medium', or 'hard'",
    )


class StepRequest(BaseModel):
    place_tower: bool = Field(default=False, description="True to place, False to pass")
    row: int = Field(default=0, ge=0, description="Grid row (0-indexed)")
    col: int = Field(default=0, ge=0, description="Grid column (0-indexed)")
    tower_type: str = Field(default="arrow", description="Tower type: arrow/cannon/magic")


# ------------------------------------------------------------------ #
# Endpoints                                                           #
# ------------------------------------------------------------------ #


def _format_observation_response(obs):
    payload = asdict(obs)
    return {
        "observation": payload,
        "reward": payload["reward"],
        "done": payload["done"],
        **payload,
    }


@app.post("/reset")
def reset(req: ResetRequest | None = None):
    """Start a new episode. Returns initial observation."""
    global env
    difficulty = req.difficulty if req is not None else "easy"
    if difficulty not in {"easy", "medium", "hard"}:
        raise HTTPException(
            status_code=400,
            detail="difficulty must be one of: easy, medium, hard",
        )
    env = TowerDefenseEnvironment(difficulty=difficulty)
    obs = env.reset()
    return _format_observation_response(obs)


@app.post("/step")
def step(req: StepRequest | None = None):
    """
    Take one action.
    Returns observation with reward and done flag.
    """
    if req is None:
        req = StepRequest()
    action = TowerDefenseAction(
        place_tower=req.place_tower,
        row=req.row,
        col=req.col,
        tower_type=req.tower_type,
    )
    try:
        result = env.step(action)
        return _format_observation_response(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
def state():
    """Get current episode metadata (step count, wave, difficulty, etc.)"""
    return asdict(env.state)


@app.get("/grade")
def grade():
    """
    Automated grading report for the current episode.
    Returns score (0-100) plus detailed breakdown.
    """
    return env.grade_episode()


@app.get("/health")
def health():
    """Server liveness check."""
    return {"status": "ok", "environment": "TowerDefense", "version": "1.0.0"}
