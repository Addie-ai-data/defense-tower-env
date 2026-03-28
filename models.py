from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from openenv.core.env_server.types import Action, Observation, State

Priority = Literal["low", "medium", "high", "urgent"]
Team = Literal[
    "billing",
    "identity",
    "privacy_ops",
    "trust_safety",
    "technical_support",
]
ActionType = Literal[
    "select_ticket",
    "set_priority",
    "assign_team",
    "add_tag",
    "request_info",
    "send_response",
    "resolve",
    "finish",
]
Resolution = Literal[
    "approve_refund",
    "offer_service_credit",
    "escalate_identity",
    "escalate_privacy",
    "escalate_safety",
    "provide_invoice",
    "await_customer_reply",
]
ResponseTemplate = Literal[
    "billing_refund_approved",
    "billing_credit_review",
    "identity_request_tenant_id",
    "privacy_verification_required",
    "safety_escalation_notice",
    "invoice_followup",
    "generic_acknowledgement",
]
InfoField = Literal[
    "order_id",
    "tenant_id",
    "affected_user_count",
    "identity_verification",
    "screenshots",
    "incident_timestamps",
]
Tag = Literal[
    "refund_request",
    "duplicate_charge",
    "invoice_request",
    "sso",
    "login_blocker",
    "enterprise",
    "data_subject_request",
    "privacy",
    "gdpr",
    "abuse_report",
    "harassment",
    "service_outage",
    "vip",
]

AVAILABLE_PRIORITIES: list[Priority] = ["low", "medium", "high", "urgent"]
AVAILABLE_TEAMS: list[Team] = [
    "billing",
    "identity",
    "privacy_ops",
    "trust_safety",
    "technical_support",
]
AVAILABLE_TAGS: list[Tag] = [
    "refund_request",
    "duplicate_charge",
    "invoice_request",
    "sso",
    "login_blocker",
    "enterprise",
    "data_subject_request",
    "privacy",
    "gdpr",
    "abuse_report",
    "harassment",
    "service_outage",
    "vip",
]
AVAILABLE_RESPONSE_TEMPLATES: list[ResponseTemplate] = [
    "billing_refund_approved",
    "billing_credit_review",
    "identity_request_tenant_id",
    "privacy_verification_required",
    "safety_escalation_notice",
    "invoice_followup",
    "generic_acknowledgement",
]
AVAILABLE_INFO_FIELDS: list[InfoField] = [
    "order_id",
    "tenant_id",
    "affected_user_count",
    "identity_verification",
    "screenshots",
    "incident_timestamps",
]
AVAILABLE_RESOLUTIONS: list[Resolution] = [
    "approve_refund",
    "offer_service_credit",
    "escalate_identity",
    "escalate_privacy",
    "escalate_safety",
    "provide_invoice",
    "await_customer_reply",
]


class SupportTriageAction(Action):
    action_type: ActionType = Field(
        ...,
        description="The workflow operation to perform on the queue.",
    )
    ticket_id: str | None = Field(
        default=None,
        description="Ticket identifier for select_ticket or explicit targeting.",
    )
    priority: Priority | None = Field(default=None)
    team: Team | None = Field(default=None)
    tag: Tag | None = Field(default=None)
    info_field: InfoField | None = Field(default=None)
    response_template: ResponseTemplate | None = Field(default=None)
    resolution: Resolution | None = Field(default=None)
    rationale: str | None = Field(
        default=None,
        description="Optional short explanation for logging/debugging.",
    )


class SupportTriageRewardSignal(BaseModel):
    progress_delta: float = 0.0
    action_penalty: float = 0.0
    completion_bonus: float = 0.0
    current_task_score: float = 0.0
    unresolved_tickets: int = 0
    explanation: str = ""
    per_ticket_scores: dict[str, float] = Field(default_factory=dict)


class TicketSummary(BaseModel):
    ticket_id: str
    subject: str
    customer_tier: str
    channel: str
    due_in_minutes: int
    status: str
    assigned_team: str | None = None
    priority: str | None = None
    tags: list[str] = Field(default_factory=list)
    requested_info: list[str] = Field(default_factory=list)
    response_template: str | None = None
    resolution: str | None = None
    score: float = 0.0


class ActiveTicketView(TicketSummary):
    customer_message: str
    account_context: str
    allowed_tags: list[str] = Field(default_factory=list)


class SupportTriageObservation(Observation):
    task_id: str
    task_title: str
    difficulty: str
    task_goal: str
    instructions: str
    queue: list[TicketSummary] = Field(default_factory=list)
    selected_ticket_id: str | None = None
    active_ticket: ActiveTicketView | None = None
    available_priorities: list[str] = Field(default_factory=lambda: list(AVAILABLE_PRIORITIES))
    available_teams: list[str] = Field(default_factory=lambda: list(AVAILABLE_TEAMS))
    available_tags: list[str] = Field(default_factory=lambda: list(AVAILABLE_TAGS))
    available_response_templates: list[str] = Field(
        default_factory=lambda: list(AVAILABLE_RESPONSE_TEMPLATES)
    )
    available_info_fields: list[str] = Field(default_factory=lambda: list(AVAILABLE_INFO_FIELDS))
    available_resolutions: list[str] = Field(default_factory=lambda: list(AVAILABLE_RESOLUTIONS))
    last_action_summary: str = ""
    tickets_completed: int = 0
    total_tickets: int = 0
    score_estimate: float = 0.0
    reward_signal: SupportTriageRewardSignal = Field(
        default_factory=SupportTriageRewardSignal
    )


class TicketWorkState(BaseModel):
    ticket_id: str
    status: str
    assigned_team: str | None = None
    priority: str | None = None
    tags: list[str] = Field(default_factory=list)
    requested_info: list[str] = Field(default_factory=list)
    response_template: str | None = None
    resolution: str | None = None
    score: float = 0.0


class SupportTriageState(State):
    task_id: str = ""
    task_title: str = ""
    difficulty: str = "easy"
    max_steps: int = 0
    selected_ticket_id: str | None = None
    current_task_score: float = 0.0
    cumulative_reward: float = 0.0
    done: bool = False
    tickets_completed: int = 0
    total_tickets: int = 0
    action_history: list[str] = Field(default_factory=list)
    tickets: list[TicketWorkState] = Field(default_factory=list)
    extra_info: dict[str, Any] = Field(default_factory=dict)
