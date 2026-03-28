---
title: Support Triage OpenEnv
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
license: mit
tags:
  - openenv
  - fastapi
  - customer-support
  - reinforcement-learning
python_version: "3.11"
---

# Support Triage OpenEnv

`Support Triage OpenEnv` is a real-world customer-support operations environment for training and evaluating agents on ticket triage, routing, escalation, and response planning.

Instead of a toy game, the environment models work that actual support teams do every day:

- assigning urgency under SLA pressure
- routing work to the correct team
- requesting missing information when needed
- choosing safe customer responses
- resolving or escalating tickets without violating policy

The environment follows the OpenEnv pattern with typed action, observation, and state models, `reset()` / `step()` / `state()` APIs, a root `openenv.yaml`, a Docker deployment path for Hugging Face Spaces, and a baseline `inference.py`.

## Why This Is Useful

Support operations are a strong agent benchmark because the job is:

- multi-step rather than one-shot
- partially observable because some fields are missing
- safety-sensitive because wrong replies can create legal or trust issues
- rewardable with deterministic graders instead of subjective free-form judging

This makes the environment useful for RL post-training, agent evaluation, tool-use experiments, and policy-abiding customer support research.

## Tasks

The environment ships with three deterministic tasks and difficulty progression:

1. `support_easy`
Billing refund triage for a duplicate annual-plan charge.

2. `support_medium`
A two-ticket queue mixing an urgent enterprise SSO outage with a low-priority invoice request.

3. `support_hard`
A three-ticket mixed queue covering GDPR privacy escalation, trust-and-safety abuse handling, and outage credit review.

Each task has a programmatic grader that returns a score in `[0.0, 1.0]` based on:

- correct priority
- correct team routing
- correct tags
- required missing-info requests
- correct response template
- correct final resolution

## Action Space

`SupportTriageAction` is a typed Pydantic model with these operations:

- `select_ticket`
- `set_priority`
- `assign_team`
- `add_tag`
- `request_info`
- `send_response`
- `resolve`
- `finish`

Structured fields include:

- `ticket_id`
- `priority`
- `team`
- `tag`
- `info_field`
- `response_template`
- `resolution`

## Observation Space

`SupportTriageObservation` includes:

- task metadata and goal
- queue summary for every ticket
- detailed view for the currently selected ticket
- allowed priorities, teams, tags, templates, and resolutions
- last action summary
- current score estimate
- typed reward breakdown in `reward_signal`

The observation is designed so an agent can act step by step without direct access to the hidden rubric.

## Reward Design

Reward is dense and shaped over the full trajectory:

- positive reward when an action increases the deterministic task score
- small negative reward for redundant or invalid actions
- completion bonus for fully resolved queues
- timeout or early-finish penalties when unresolved work remains

The environment score remains a clean `[0.0, 1.0]` grader, while the step reward gives useful learning signal throughout the episode.

## Project Layout

```text
.
|-- __init__.py
|-- client.py
|-- models.py
|-- inference.py
|-- openenv.yaml
|-- pyproject.toml
|-- requirements.txt
|-- Dockerfile
`-- server/
    |-- app.py
    |-- support_triage_environment.py
    |-- requirements.txt
    `-- Dockerfile
```

## Local Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the environment locally:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Run OpenEnv validation:

```bash
openenv validate .
```

Build the container:

```bash
docker build -t support-triage-openenv .
docker run -p 8000:8000 support-triage-openenv
```

## Hugging Face Spaces

This repo is configured for a Docker Space.

Required HF metadata is set in the README frontmatter:

- `sdk: docker`
- `app_port: 8000`
- `tags: [openenv, ...]`

The Space should expose the FastAPI/OpenEnv app served by `uvicorn server.app:app`.

## Baseline Inference

The root `inference.py` supports two modes:

- `llm`: OpenAI-compatible planner using `OPENAI_API_KEY` or `HF_TOKEN`, `API_BASE_URL`, and `MODEL_NAME`
- `heuristic`: deterministic fallback for offline smoke tests

Example:

```bash
python inference.py --agent heuristic
python inference.py --agent llm
```

Environment variables expected by the LLM baseline:

- `OPENAI_API_KEY`
- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN` as an optional fallback API token

## Reproducible Baseline Scores

Deterministic heuristic baseline:

- `support_easy`: `1.000`
- `support_medium`: `1.000`
- `support_hard`: `0.985`
- average: `0.995`

Exact LLM-backed scores depend on the chosen model, but the script uses `temperature=0` and a constrained JSON action format for stable behavior.

## Notes

- The grader is deterministic by construction.
- Hidden rubric fields are not exposed directly in the observation.
- The environment stays within small CPU and memory limits and does not require external services to run.
