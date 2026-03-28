from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

try:
    from .models import SupportTriageAction, SupportTriageObservation
    from .server.support_triage_environment import SupportTriageEnvironment
except ImportError:
    from models import SupportTriageAction, SupportTriageObservation
    from server.support_triage_environment import SupportTriageEnvironment

ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "outputs" / "evals" / "baseline_scores.json"
SYSTEM_PROMPT = """
You are a careful customer-support triage agent.
Choose exactly one next action for the current queue state.

Rules:
- Prefer the highest-risk unresolved ticket.
- Use only the allowed structured values from the observation.
- Ask for required missing information before closing privacy or identity escalations.
- Output JSON only.
""".strip()


def next_heuristic_action(observation: SupportTriageObservation) -> SupportTriageAction:
    queue = sorted(
        [ticket for ticket in observation.queue if ticket.status != "resolved"],
        key=lambda ticket: ticket.due_in_minutes,
    )
    if not queue:
        return SupportTriageAction(action_type="finish")

    focus = queue[0]
    if observation.selected_ticket_id != focus.ticket_id:
        return SupportTriageAction(action_type="select_ticket", ticket_id=focus.ticket_id)

    active = observation.active_ticket
    if active is None:
        return SupportTriageAction(action_type="select_ticket", ticket_id=focus.ticket_id)

    text = f"{active.subject}\n{active.customer_message}\n{active.account_context}".lower()

    if "charged twice" in text or "duplicate" in text:
        target = {
            "priority": "high",
            "team": "billing",
            "tags": ["refund_request", "duplicate_charge"],
            "response_template": "billing_refund_approved",
            "resolution": "approve_refund",
            "required_info": [],
        }
    elif "okta" in text or "sso" in text or "sign in" in text:
        target = {
            "priority": "urgent",
            "team": "identity",
            "tags": ["sso", "login_blocker"],
            "response_template": "identity_request_tenant_id",
            "resolution": "escalate_identity",
            "required_info": ["tenant_id"],
        }
    elif "vat invoice" in text or "invoice" in text:
        target = {
            "priority": "low",
            "team": "billing",
            "tags": ["invoice_request"],
            "response_template": "invoice_followup",
            "resolution": "provide_invoice",
            "required_info": [],
        }
    elif "gdpr" in text or "deleted support transcript" in text or "former colleague" in text:
        target = {
            "priority": "high",
            "team": "privacy_ops",
            "tags": ["data_subject_request", "privacy", "gdpr"],
            "response_template": "privacy_verification_required",
            "resolution": "escalate_privacy",
            "required_info": ["identity_verification"],
        }
    elif "harassment" in text or "threatening messages" in text:
        target = {
            "priority": "urgent",
            "team": "trust_safety",
            "tags": ["abuse_report", "harassment"],
            "response_template": "safety_escalation_notice",
            "resolution": "escalate_safety",
            "required_info": [],
        }
    else:
        target = {
            "priority": "high",
            "team": "billing",
            "tags": ["service_outage", "refund_request"],
            "response_template": "billing_credit_review",
            "resolution": "offer_service_credit",
            "required_info": [],
        }

    if "enterprise" in text and "enterprise" not in active.tags and "enterprise" in active.allowed_tags:
        return SupportTriageAction(action_type="add_tag", tag="enterprise")
    if "vip" in text and "vip" not in active.tags and "vip" in active.allowed_tags:
        return SupportTriageAction(action_type="add_tag", tag="vip")
    if active.priority != target["priority"]:
        return SupportTriageAction(action_type="set_priority", priority=target["priority"])
    if active.assigned_team != target["team"]:
        return SupportTriageAction(action_type="assign_team", team=target["team"])
    for tag in target["tags"]:
        if tag in active.allowed_tags and tag not in active.tags:
            return SupportTriageAction(action_type="add_tag", tag=tag)
    for info_field in target["required_info"]:
        if info_field not in active.requested_info:
            return SupportTriageAction(action_type="request_info", info_field=info_field)
    if active.response_template != target["response_template"]:
        return SupportTriageAction(
            action_type="send_response",
            response_template=target["response_template"],
        )
    if active.resolution != target["resolution"]:
        return SupportTriageAction(action_type="resolve", resolution=target["resolution"])
    return SupportTriageAction(action_type="finish")


def build_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("HF_TOKEN")
    base_url = os.getenv("API_BASE_URL")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=base_url or None)


def llm_action(client: OpenAI | None, observation: SupportTriageObservation) -> SupportTriageAction:
    if client is None:
        return next_heuristic_action(observation)

    payload = observation.model_dump(mode="json")
    user_prompt = json.dumps(payload, indent=2, sort_keys=True)
    model_name = os.getenv("MODEL_NAME", "gpt-4.1-mini")

    try:
        completion = client.chat.completions.create(
            model=model_name,
            temperature=0,
            max_tokens=250,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Return a JSON object matching SupportTriageAction. Observation:\n"
                        + user_prompt
                    ),
                },
            ],
        )
        content = completion.choices[0].message.content or "{}"
        return SupportTriageAction.model_validate_json(content)
    except Exception:
        return next_heuristic_action(observation)


def run_episode(task_id: str, agent: str, client: OpenAI | None) -> dict[str, Any]:
    env = SupportTriageEnvironment()
    observation = env.reset(task_id=task_id)

    while not observation.done:
        action = llm_action(client, observation) if agent == "llm" else next_heuristic_action(observation)
        observation = env.step(action)

    state = env.state
    return {
        "task_id": task_id,
        "difficulty": state.difficulty,
        "score": round(state.current_task_score, 4),
        "cumulative_reward": round(state.cumulative_reward, 4),
        "steps": state.step_count,
        "tickets_completed": state.tickets_completed,
        "total_tickets": state.total_tickets,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline inference on support triage tasks.")
    parser.add_argument(
        "--agent",
        choices=["llm", "heuristic"],
        default="llm",
        help="Planner to use for the baseline run.",
    )
    args = parser.parse_args()

    client = build_openai_client() if args.agent == "llm" else None
    results = [
        run_episode(task_id, args.agent, client)
        for task_id in SupportTriageEnvironment.available_tasks()
    ]
    average_score = round(sum(result["score"] for result in results) / len(results), 4)

    summary = {
        "agent": args.agent,
        "model_name": os.getenv("MODEL_NAME", ""),
        "api_base_url": os.getenv("API_BASE_URL", ""),
        "results": results,
        "average_score": average_score,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
