from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

try:
    from ..models import (
        AVAILABLE_TAGS,
        ActiveTicketView,
        SupportTriageAction,
        SupportTriageObservation,
        SupportTriageRewardSignal,
        SupportTriageState,
        TicketSummary,
        TicketWorkState,
    )
except ImportError:
    from models import (
        AVAILABLE_TAGS,
        ActiveTicketView,
        SupportTriageAction,
        SupportTriageObservation,
        SupportTriageRewardSignal,
        SupportTriageState,
        TicketSummary,
        TicketWorkState,
    )

FIELD_WEIGHTS = {
    "priority": 0.18,
    "team": 0.22,
    "tags": 0.18,
    "required_info": 0.12,
    "response": 0.15,
    "resolution": 0.15,
}


@dataclass(frozen=True)
class TicketSpec:
    ticket_id: str
    subject: str
    customer_tier: str
    channel: str
    customer_message: str
    account_context: str
    due_in_minutes: int
    allowed_tags: tuple[str, ...]
    expected_priority: str
    expected_team: str
    expected_tags: tuple[str, ...]
    expected_response: str
    expected_resolution: str
    required_info: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    title: str
    difficulty: str
    goal: str
    instructions: str
    max_steps: int
    tickets: tuple[TicketSpec, ...]


@dataclass
class TicketRuntime:
    spec: TicketSpec
    status: str = "open"
    assigned_team: str | None = None
    priority: str | None = None
    tags: set[str] = field(default_factory=set)
    requested_info: set[str] = field(default_factory=set)
    response_template: str | None = None
    resolution: str | None = None


TASKS: dict[str, TaskSpec] = {
    "support_easy": TaskSpec(
        task_id="support_easy",
        title="Duplicate Charge Refund",
        difficulty="easy",
        goal=(
            "Process a single billing ticket about a duplicate charge. The agent should "
            "prioritize correctly, route it to billing, tag it, reply with the right "
            "template, and choose the right resolution."
        ),
        instructions=(
            "Work like a human support lead. Use one action per step. Resolve the queue "
            "with the highest-quality triage, not the fastest shortcut."
        ),
        max_steps=7,
        tickets=(
            TicketSpec(
                ticket_id="BIL-1001",
                subject="Charged twice for the annual plan renewal",
                customer_tier="standard",
                channel="email",
                customer_message=(
                    "Hi team, I renewed our annual plan once, but my card shows two $49 "
                    "charges for invoice INV-2048. Can you reverse the duplicate?"
                ),
                account_context=(
                    "Customer has one active workspace, healthy payment history, and no "
                    "prior refund abuse flags."
                ),
                due_in_minutes=90,
                allowed_tags=("refund_request", "duplicate_charge", "vip"),
                expected_priority="high",
                expected_team="billing",
                expected_tags=("refund_request", "duplicate_charge"),
                expected_response="billing_refund_approved",
                expected_resolution="approve_refund",
            ),
        ),
    ),
    "support_medium": TaskSpec(
        task_id="support_medium",
        title="SSO Lockout Queue",
        difficulty="medium",
        goal=(
            "Triage a two-ticket queue: an urgent enterprise SSO outage that needs fast "
            "escalation and an invoice follow-up that should not steal urgency from the outage."
        ),
        instructions=(
            "Balance SLA urgency with correctness. Collect required missing info before "
            "closing an escalation ticket."
        ),
        max_steps=12,
        tickets=(
            TicketSpec(
                ticket_id="ID-2204",
                subject="SSO failure after Okta certificate rotation",
                customer_tier="enterprise",
                channel="web",
                customer_message=(
                    "We rotated our Okta certificate this morning and now 14 employees "
                    "cannot sign in. I do not have the tenant ID handy yet, but this is "
                    "blocking payroll review for finance."
                ),
                account_context=(
                    "Enterprise account. Admin contact is verified. Workspace is in a paid "
                    "annual contract with a 30-minute escalation target."
                ),
                due_in_minutes=25,
                allowed_tags=("sso", "login_blocker", "enterprise", "service_outage"),
                expected_priority="urgent",
                expected_team="identity",
                expected_tags=("sso", "login_blocker", "enterprise"),
                expected_response="identity_request_tenant_id",
                expected_resolution="escalate_identity",
                required_info=("tenant_id",),
            ),
            TicketSpec(
                ticket_id="BIL-2205",
                subject="Need a VAT invoice for February",
                customer_tier="standard",
                channel="email",
                customer_message=(
                    "Could you send our February VAT invoice? Accounting needs the PDF "
                    "before month-end close."
                ),
                account_context=(
                    "Invoice exists in the billing system. No payment dispute or outage flag "
                    "on the account."
                ),
                due_in_minutes=360,
                allowed_tags=("invoice_request", "refund_request", "vip"),
                expected_priority="low",
                expected_team="billing",
                expected_tags=("invoice_request",),
                expected_response="invoice_followup",
                expected_resolution="provide_invoice",
            ),
        ),
    ),
    "support_hard": TaskSpec(
        task_id="support_hard",
        title="Compliance and Abuse Escalation Queue",
        difficulty="hard",
        goal=(
            "Handle a mixed queue containing privacy, trust-and-safety, and outage-credit "
            "tickets without breaking compliance or missing the most urgent work."
        ),
        instructions=(
            "Use careful routing and the right escalation templates. Privacy requests must "
            "verify identity first, and safety complaints should be escalated without promising "
            "outcomes you cannot guarantee."
        ),
        max_steps=16,
        tickets=(
            TicketSpec(
                ticket_id="PRV-3301",
                subject="GDPR export request for deleted support chats",
                customer_tier="vip",
                channel="email",
                customer_message=(
                    "I need every deleted support transcript from our EU workspace, including "
                    "the chats my former colleague handled before leaving the company. Please "
                    "send them today."
                ),
                account_context=(
                    "Enterprise EU account with an active DPA. Requestor is listed as an admin "
                    "but identity verification for this session has not been completed."
                ),
                due_in_minutes=120,
                allowed_tags=("data_subject_request", "privacy", "gdpr", "vip"),
                expected_priority="high",
                expected_team="privacy_ops",
                expected_tags=("data_subject_request", "privacy", "gdpr", "vip"),
                expected_response="privacy_verification_required",
                expected_resolution="escalate_privacy",
                required_info=("identity_verification",),
            ),
            TicketSpec(
                ticket_id="SAFE-3302",
                subject="Seller harassment report with screenshot evidence",
                customer_tier="standard",
                channel="web",
                customer_message=(
                    "A marketplace seller has been sending threatening messages to our creator "
                    "manager. We already attached screenshots and need someone to review this urgently."
                ),
                account_context=(
                    "Attachments already present in the ticket. Prior abuse report on the same "
                    "seller exists from last quarter."
                ),
                due_in_minutes=20,
                allowed_tags=("abuse_report", "harassment", "vip"),
                expected_priority="urgent",
                expected_team="trust_safety",
                expected_tags=("abuse_report", "harassment"),
                expected_response="safety_escalation_notice",
                expected_resolution="escalate_safety",
            ),
            TicketSpec(
                ticket_id="BIL-3303",
                subject="Requesting service credit after EU region outage",
                customer_tier="enterprise",
                channel="email",
                customer_message=(
                    "Your EU region outage took our team offline for nearly two hours. Can you "
                    "review a prorated credit for March?"
                ),
                account_context=(
                    "Account is healthy. Incident INC-7788 confirms the outage window and the "
                    "customer qualifies for credit review."
                ),
                due_in_minutes=240,
                allowed_tags=("service_outage", "refund_request", "vip"),
                expected_priority="high",
                expected_team="billing",
                expected_tags=("service_outage", "refund_request"),
                expected_response="billing_credit_review",
                expected_resolution="offer_service_credit",
            ),
        ),
    ),
}


class SupportTriageEnvironment(
    Environment[SupportTriageAction, SupportTriageObservation, SupportTriageState]
):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._task_spec: TaskSpec = TASKS["support_easy"]
        self._tickets: dict[str, TicketRuntime] = {}
        self._episode_id = ""
        self._selected_ticket_id: str | None = None
        self._step_count = 0
        self._done = False
        self._cumulative_reward = 0.0
        self._last_action_summary = "Environment ready."
        self._action_history: list[str] = []

    @classmethod
    def available_tasks(cls) -> list[str]:
        return list(TASKS.keys())

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        task_id: str | None = None,
        difficulty: str | None = None,
        **kwargs: Any,
    ) -> SupportTriageObservation:
        del seed, kwargs
        self._task_spec = self._resolve_task(task_id=task_id, difficulty=difficulty)
        self._episode_id = episode_id or str(uuid4())[:8]
        self._tickets = {
            ticket.ticket_id: TicketRuntime(spec=ticket) for ticket in self._task_spec.tickets
        }
        self._selected_ticket_id = self._task_spec.tickets[0].ticket_id
        self._step_count = 0
        self._done = False
        self._cumulative_reward = 0.0
        self._last_action_summary = (
            f"Loaded task '{self._task_spec.title}'. Start by selecting or triaging "
            f"ticket {self._selected_ticket_id}."
        )
        self._action_history = ["reset"]
        return self._build_observation(
            reward=0.0,
            reward_signal=SupportTriageRewardSignal(
                current_task_score=self._task_score(),
                unresolved_tickets=self._unresolved_count(),
                per_ticket_scores=self._per_ticket_scores(),
                explanation="New episode started.",
            ),
        )

    def step(
        self,
        action: SupportTriageAction,
        timeout_s: float | None = None,
        **kwargs: Any,
    ) -> SupportTriageObservation:
        del timeout_s, kwargs
        if not self._tickets:
            return self.reset()
        if self._done:
            return self._build_observation(
                reward=0.0,
                reward_signal=SupportTriageRewardSignal(
                    current_task_score=self._task_score(),
                    unresolved_tickets=self._unresolved_count(),
                    per_ticket_scores=self._per_ticket_scores(),
                    explanation="Episode already finished.",
                ),
            )

        self._step_count += 1
        previous_score = self._task_score()
        action_penalty = 0.0
        completion_bonus = 0.0
        explanation = ""

        try:
            explanation, action_penalty = self._apply_action(action)
        except ValueError as exc:
            explanation = str(exc)
            action_penalty = -0.12

        current_score = self._task_score()
        progress_delta = round(current_score - previous_score, 4)
        reward = round((progress_delta * 2.2) + action_penalty, 4)

        if self._all_tickets_resolved():
            self._done = True
            completion_bonus += round(0.2 + (current_score * 0.4), 4)
            reward += completion_bonus
            explanation = explanation or "All tickets resolved."
        elif action.action_type == "finish":
            self._done = True
            unresolved_penalty = round(self._unresolved_count() * -0.08, 4)
            reward += unresolved_penalty
            action_penalty += unresolved_penalty
            explanation = explanation or "Agent ended the queue early."
        elif self._step_count >= self._task_spec.max_steps:
            self._done = True
            timeout_penalty = round(self._unresolved_count() * -0.06, 4)
            reward += timeout_penalty
            action_penalty += timeout_penalty
            explanation = explanation or "Step budget exhausted."

        reward = round(reward, 4)
        self._cumulative_reward = round(self._cumulative_reward + reward, 4)
        self._last_action_summary = explanation
        self._action_history.append(
            f"{self._step_count}: {action.action_type} -> {explanation} ({reward:+.2f})"
        )

        reward_signal = SupportTriageRewardSignal(
            progress_delta=progress_delta,
            action_penalty=round(action_penalty, 4),
            completion_bonus=round(completion_bonus, 4),
            current_task_score=current_score,
            unresolved_tickets=self._unresolved_count(),
            per_ticket_scores=self._per_ticket_scores(),
            explanation=explanation,
        )
        return self._build_observation(reward=reward, reward_signal=reward_signal)

    @property
    def state(self) -> SupportTriageState:
        tickets = [
            TicketWorkState(
                ticket_id=runtime.spec.ticket_id,
                status=runtime.status,
                assigned_team=runtime.assigned_team,
                priority=runtime.priority,
                tags=sorted(runtime.tags),
                requested_info=sorted(runtime.requested_info),
                response_template=runtime.response_template,
                resolution=runtime.resolution,
                score=round(self._ticket_score(runtime), 4),
            )
            for runtime in self._tickets.values()
        ]
        return SupportTriageState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            task_id=self._task_spec.task_id,
            task_title=self._task_spec.title,
            difficulty=self._task_spec.difficulty,
            max_steps=self._task_spec.max_steps,
            selected_ticket_id=self._selected_ticket_id,
            current_task_score=round(self._task_score(), 4),
            cumulative_reward=self._cumulative_reward,
            done=self._done,
            tickets_completed=len([t for t in self._tickets.values() if t.status == "resolved"]),
            total_tickets=len(self._tickets),
            action_history=self._action_history[-12:],
            tickets=tickets,
            extra_info={"last_action_summary": self._last_action_summary},
        )

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="SupportTriageEnvironment",
            description=(
                "A real-world customer support operations environment for ticket triage, "
                "routing, escalation, and SLA-aware response planning."
            ),
            version="0.1.0",
        )

    def _resolve_task(self, task_id: str | None, difficulty: str | None) -> TaskSpec:
        if task_id:
            if task_id not in TASKS:
                raise ValueError(f"Unknown task_id '{task_id}'. Available: {list(TASKS)}")
            return TASKS[task_id]
        if difficulty:
            difficulty = difficulty.lower()
            for spec in TASKS.values():
                if spec.difficulty == difficulty:
                    return spec
            raise ValueError(f"Unknown difficulty '{difficulty}'.")
        return TASKS["support_easy"]

    def _apply_action(self, action: SupportTriageAction) -> tuple[str, float]:
        if action.action_type == "finish":
            return "Marked queue as finished.", 0.0

        ticket = self._target_ticket(action)
        if action.action_type == "select_ticket":
            if ticket is None:
                raise ValueError("select_ticket requires a valid ticket_id.")
            if self._selected_ticket_id == ticket.spec.ticket_id:
                return f"Ticket {ticket.spec.ticket_id} was already selected.", -0.02
            self._selected_ticket_id = ticket.spec.ticket_id
            return f"Selected ticket {ticket.spec.ticket_id}.", 0.02

        if ticket is None:
            raise ValueError("No active ticket is selected.")

        if action.action_type == "set_priority":
            if action.priority is None:
                raise ValueError("set_priority requires a priority value.")
            previous = ticket.priority
            ticket.priority = action.priority
            if previous == action.priority:
                return f"Priority already set to {action.priority}.", -0.02
            return f"Set priority for {ticket.spec.ticket_id} to {action.priority}.", 0.0

        if action.action_type == "assign_team":
            if action.team is None:
                raise ValueError("assign_team requires a team value.")
            previous = ticket.assigned_team
            ticket.assigned_team = action.team
            if previous == action.team:
                return f"Team already set to {action.team}.", -0.02
            return f"Assigned {ticket.spec.ticket_id} to {action.team}.", 0.0

        if action.action_type == "add_tag":
            if action.tag is None:
                raise ValueError("add_tag requires a tag value.")
            if action.tag not in AVAILABLE_TAGS:
                raise ValueError(f"Tag '{action.tag}' is not supported.")
            if action.tag in ticket.tags:
                return f"Tag {action.tag} already present on {ticket.spec.ticket_id}.", -0.02
            ticket.tags.add(action.tag)
            return f"Added tag {action.tag} to {ticket.spec.ticket_id}.", 0.0

        if action.action_type == "request_info":
            if action.info_field is None:
                raise ValueError("request_info requires an info_field value.")
            if action.info_field in ticket.requested_info:
                return (
                    f"Info field {action.info_field} was already requested for "
                    f"{ticket.spec.ticket_id}.",
                    -0.02,
                )
            ticket.requested_info.add(action.info_field)
            return (
                f"Requested {action.info_field} from the customer on {ticket.spec.ticket_id}.",
                0.0,
            )

        if action.action_type == "send_response":
            if action.response_template is None:
                raise ValueError("send_response requires a response_template value.")
            if ticket.response_template == action.response_template:
                return (
                    f"Response template {action.response_template} already sent for "
                    f"{ticket.spec.ticket_id}.",
                    -0.02,
                )
            ticket.response_template = action.response_template
            return (
                f"Set customer reply for {ticket.spec.ticket_id} to {action.response_template}.",
                0.0,
            )

        if action.action_type == "resolve":
            if action.resolution is None:
                raise ValueError("resolve requires a resolution value.")
            ticket.resolution = action.resolution
            ticket.status = "resolved"
            return (
                f"Resolved {ticket.spec.ticket_id} with resolution {action.resolution}.",
                0.0,
            )

        raise ValueError(f"Unsupported action_type '{action.action_type}'.")

    def _target_ticket(self, action: SupportTriageAction) -> TicketRuntime | None:
        if action.ticket_id:
            if action.ticket_id not in self._tickets:
                raise ValueError(f"Unknown ticket_id '{action.ticket_id}'.")
            return self._tickets[action.ticket_id]
        if self._selected_ticket_id:
            return self._tickets[self._selected_ticket_id]
        return None

    def _ticket_score(self, runtime: TicketRuntime) -> float:
        spec = runtime.spec
        weighted_score = 0.0
        active_weight = 0.0

        def add_component(name: str, value: float, include: bool = True) -> None:
            nonlocal weighted_score, active_weight
            if not include:
                return
            active_weight += FIELD_WEIGHTS[name]
            weighted_score += FIELD_WEIGHTS[name] * value

        add_component("priority", 1.0 if runtime.priority == spec.expected_priority else 0.0)
        add_component("team", 1.0 if runtime.assigned_team == spec.expected_team else 0.0)

        expected_tags = set(spec.expected_tags)
        if expected_tags:
            matched = len(runtime.tags & expected_tags)
            extras = len(runtime.tags - expected_tags)
            tag_value = max(0.0, (matched / len(expected_tags)) - (extras * 0.15))
            add_component("tags", min(tag_value, 1.0))

        required_info = set(spec.required_info)
        add_component(
            "required_info",
            (
                len(runtime.requested_info & required_info) / len(required_info)
                if required_info
                else 0.0
            ),
            include=bool(required_info),
        )
        add_component("response", 1.0 if runtime.response_template == spec.expected_response else 0.0)
        add_component("resolution", 1.0 if runtime.resolution == spec.expected_resolution else 0.0)

        if active_weight == 0:
            return 0.0
        return round(weighted_score / active_weight, 4)

    def _per_ticket_scores(self) -> dict[str, float]:
        return {
            ticket_id: round(self._ticket_score(runtime), 4)
            for ticket_id, runtime in self._tickets.items()
        }

    def _task_score(self) -> float:
        if not self._tickets:
            return 0.0
        return round(
            sum(self._ticket_score(runtime) for runtime in self._tickets.values())
            / len(self._tickets),
            4,
        )

    def _all_tickets_resolved(self) -> bool:
        return bool(self._tickets) and all(
            runtime.status == "resolved" for runtime in self._tickets.values()
        )

    def _unresolved_count(self) -> int:
        return len([runtime for runtime in self._tickets.values() if runtime.status != "resolved"])

    def _ticket_summary(self, runtime: TicketRuntime) -> TicketSummary:
        return TicketSummary(
            ticket_id=runtime.spec.ticket_id,
            subject=runtime.spec.subject,
            customer_tier=runtime.spec.customer_tier,
            channel=runtime.spec.channel,
            due_in_minutes=runtime.spec.due_in_minutes,
            status=runtime.status,
            assigned_team=runtime.assigned_team,
            priority=runtime.priority,
            tags=sorted(runtime.tags),
            requested_info=sorted(runtime.requested_info),
            response_template=runtime.response_template,
            resolution=runtime.resolution,
            score=round(self._ticket_score(runtime), 4),
        )

    def _active_ticket_view(self) -> ActiveTicketView | None:
        if self._selected_ticket_id is None:
            return None
        runtime = self._tickets[self._selected_ticket_id]
        summary = self._ticket_summary(runtime)
        return ActiveTicketView(
            **summary.model_dump(),
            customer_message=runtime.spec.customer_message,
            account_context=runtime.spec.account_context,
            allowed_tags=list(runtime.spec.allowed_tags),
        )

    def _build_observation(
        self,
        reward: float,
        reward_signal: SupportTriageRewardSignal,
    ) -> SupportTriageObservation:
        queue = [self._ticket_summary(runtime) for runtime in self._tickets.values()]
        observation = SupportTriageObservation(
            task_id=self._task_spec.task_id,
            task_title=self._task_spec.title,
            difficulty=self._task_spec.difficulty,
            task_goal=self._task_spec.goal,
            instructions=self._task_spec.instructions,
            queue=queue,
            selected_ticket_id=self._selected_ticket_id,
            active_ticket=self._active_ticket_view(),
            last_action_summary=self._last_action_summary,
            tickets_completed=len([ticket for ticket in self._tickets.values() if ticket.status == "resolved"]),
            total_tickets=len(self._tickets),
            score_estimate=self._task_score(),
            reward_signal=reward_signal,
            reward=reward,
            done=self._done,
            metadata={
                "task_id": self._task_spec.task_id,
                "difficulty": self._task_spec.difficulty,
            },
        )
        return self._apply_transform(observation)
