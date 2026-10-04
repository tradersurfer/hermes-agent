"""Department subagent registry for the CEO agent.

Every spec here is a verbatim replay of a subagent that was actually spawned in
the JECI-Gang group chat on 2026-10-01/02. Names, goals, toolsets and role are
preserved exactly so a dispatch from this registry reproduces the session.

Usage (from an active Hermes turn, e.g. via the `departments-subagents` skill):

    from departments_subagents import build_tasks
    build_tasks("ceo")            # -> list of delegate_task task dicts
    build_tasks()                 # -> every department, flattened
    list_subagents()              # -> printable table

The runner never imports tools.delegate_tool directly; it emits task payloads
for the parent's `delegate_task` call so all child-construction, tool-resolution
restoration and cost rollup stay on the host-owned path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Iterable

# Toolsets the session's subagents ran with. `None` means "inherit the parent's
# enabled toolsets", which is what every recorded delegation did (toolsets=None).
INHERIT = None

# Leaf role: no delegate_task / clarify / memory / send_message / cronjob,
# keeps execute_code. Every recorded delegation used role="leaf".
LEAF_ROLE = "leaf"


@dataclass(frozen=True)
class SubagentSpec:
    """One department subagent."""

    name: str
    department: str
    goal: str
    context: str = ""
    toolsets: tuple[str, ...] | None = INHERIT
    role: str = LEAF_ROLE
    model: str | None = None
    origin_session: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_task(self) -> dict:
        """Render as one entry of a `delegate_task(tasks=[...])` batch."""
        task: dict = {"goal": self.goal}
        if self.context:
            task["context"] = self.context
        if self.toolsets:
            task["toolsets"] = list(self.toolsets)
        if self.model:
            task["model"] = self.model
        return task

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Executive department (spawned by @ceo-agent, session 20261001_224013_843deb)
# --------------------------------------------------------------------------

CEO_AGENT = "ceo-agent"
CTO_AGENT = "cto-agent"
COO_AGENT = "coo-agent"

NORTHSTAR_CONTEXT = (
    "NorthStar Home Services — residential HVAC / plumbing / electrical, "
    "Washington DC and Northern Virginia. Target of a JECI / Dynasty "
    "acquisition due-diligence and turnaround. Working capital for JECI is "
    "limited; every recommendation must be justified against EBITDA impact "
    "and capital cost. Show the math for every claim."
)

SPECS: tuple[SubagentSpec, ...] = (
    # ---------------- Executive (CEO agent) ----------------
    SubagentSpec(
        name="chief-of-staff",
        department=CEO_AGENT,
        goal=(
            "Chief of Staff for NorthStar acquisition — set up executive audit "
            "trail: list known facts, identify critical data gaps, define "
            "decision gates, track timeline and interlocks. Do NOT do the final "
            "recommendation."
        ),
        origin_session="20261001_224013_843deb",
        tags=("executive", "audit-trail", "process"),
    ),
    SubagentSpec(
        name="strategy-analyst",
        department=CEO_AGENT,
        goal=(
            "Strategy Analyst for NorthStar acquisition — preliminary strategic "
            "analysis: service-line mix & concentration risk, market position in "
            "DC/NoVA, competitive landscape, strategic fit for JECI consolidator, "
            "synergies (centralized dispatch, cross-selling, shared marketing), "
            "strategic risks, value creation opportunities."
        ),
        context=NORTHSTAR_CONTEXT,
        origin_session="20261001_224013_843deb",
        tags=("executive", "strategy", "market"),
    ),
    SubagentSpec(
        name="decision-risk-analyst",
        department=CEO_AGENT,
        goal=(
            "Decision & Risk Analyst for NorthStar — build initial risk register "
            "from 17 problems across financial/operational/legal/tech/market/"
            "reputational risk. Assign probability/impact. Develop decision "
            "criteria framework. Create 3 scenarios (downside/base/upside) with "
            "value ranges. Analyze decision-critical risks."
        ),
        context=NORTHSTAR_CONTEXT,
        origin_session="20261001_224013_843deb",
        tags=("executive", "risk", "scenarios"),
    ),
    # ---------------- Technology (CTO agent) ----------------
    SubagentSpec(
        name="tech-architecture-lead",
        department=CTO_AGENT,
        goal=(
            "Design NorthStar's target technology architecture and 90-day "
            "roadmap. Classify every current system as KEEP / REPLACE / "
            "INTEGRATE / AUTOMATE / DEFER. Identify the single system of record "
            "for each domain: customers, jobs, financials, employees, marketing, "
            "communications. Distinguish KEEPS from NEED-TO-ROPE IN before "
            "closing. No blanket 'rip and replace' — justify each call with "
            "effort vs EBITDA impact. Return a ranked roadmap with day-0 / 30 / "
            "60 / 90 milestones and the integration approach between SOR domains."
        ),
        context=NORTHSTAR_CONTEXT,
        origin_session="20261001_224525_8c3aea",
        tags=("technology", "architecture", "roadmap"),
    ),
    SubagentSpec(
        name="crm-data-lead",
        department=CTO_AGENT,
        goal=(
            "Lead the CRM and customer data architecture workstream. Inventory "
            "all 4 overlapping customer databases and map their schema "
            "overlap/gaps. Recommend ONE system of record for customers and "
            "jobs, with a data migration approach (ETL sequence, dedupe "
            "strategy, survivorship rules). Address the AOV/job-count "
            "attribution problem the COO flagged — identify which DB holds "
            "authoritative revenue and job data. Produce a 30/60/90 migration "
            "plan with risk points (data loss, downtime, referential integrity). "
            "Recommend whether JECI must obtain DB exports from the seller "
            "BEFORE closing for diligence. Return a data-quality risk rating."
        ),
        context=NORTHSTAR_CONTEXT,
        origin_session="20261001_224525_8c3aea",
        tags=("technology", "data", "migration"),
    ),
    SubagentSpec(
        name="automation-analyst",
        department=CTO_AGENT,
        goal=(
            "Identify and prioritize automation opportunities across NorthStar's "
            "operations. Focus: dispatch (spreadsheets), scheduling "
            "optimization, customer communications (appointment reminders, "
            "post-service follow-ups, membership renewals), reporting/BI "
            "(centralized dashboards), lead attribution. Separate QUICK WINS "
            "(30 days, low capital) from longer-term automations. For each, "
            "estimate effort and EBITDA impact. JECI has limited capital. "
            "Return ranked list with effort/impact scoring and 90-day execution "
            "plan."
        ),
        context=NORTHSTAR_CONTEXT,
        origin_session="20261001_224525_8c3aea",
        tags=("technology", "automation", "quick-wins"),
    ),
    SubagentSpec(
        name="security-iam-lead",
        department=CTO_AGENT,
        goal=(
            "Assess NorthStar's security and infrastructure posture. Recommend "
            "IAM strategy: SSO, RBAC by role (field tech, dispatcher, admin, "
            "sales, management), least-privilege. Security requirements for "
            "protecting 38K customer records, 2,850 member records, financial "
            "data. Recommend infrastructure approach (cloud-first vs on-prem, "
            "backup strategy, monitoring). Produce 90-day IAM + security "
            "roadmap. Flag compliance (PCI for payments, data protection). "
            "Capital-efficient and staged. Note COO flagged unit-economics tied "
            "to data integrity — security must ensure audit trail integrity."
        ),
        context=NORTHSTAR_CONTEXT,
        origin_session="20261001_224525_8c3aea",
        tags=("technology", "security", "iam", "compliance"),
    ),
    # ---------------- Field operations (COO agent) ----------------
    SubagentSpec(
        name="field-operations-analyst",
        department=COO_AGENT,
        goal=(
            "You are the Field Operations Analyst for a due-diligence "
            "turnaround of NorthStar Home Services (residential HVAC/plumbing/"
            "electrical, Washington DC / NoVA). Produce a rigorous operational "
            "field-ops assessment with numbers, not platitudes. Show the math "
            "for every claim."
        ),
        origin_session="20261001_223906_650b71",
        tags=("operations", "field", "due-diligence"),
    ),
    SubagentSpec(
        name="dispatch-scheduling-analyst",
        department=COO_AGENT,
        goal=(
            "You are the Dispatch & Scheduling Analyst for a due-diligence "
            "turnaround of NorthStar Home Services (residential HVAC/plumbing/"
            "electrical, Washington DC / NoVA). Produce a rigorous "
            "dispatch/scheduling assessment with numbers. Show the math for "
            "every claim."
        ),
        origin_session="20261001_223906_650b71",
        tags=("operations", "dispatch", "scheduling"),
    ),
    SubagentSpec(
        name="sop-process-analyst",
        department=COO_AGENT,
        goal=(
            "You are the SOP & Process Analyst for a due-diligence turnaround "
            "of NorthStar Home Services (residential HVAC/plumbing/electrical, "
            "DC/NoVA). Produce a rigorous process/SOP assessment with numbers, "
            "prioritized by financial value and implementation friction."
        ),
        origin_session="20261001_223906_650b71",
        tags=("operations", "sop", "process"),
    ),
    SubagentSpec(
        name="customer-experience-analyst",
        department=COO_AGENT,
        goal=(
            "You are the Customer Experience Analyst for a due-diligence "
            "turnaround of NorthStar Home Services (residential HVAC/plumbing/"
            "electrical, DC/NoVA). Produce a rigorous CX analysis with numbers: "
            "complaints, reviews, NPS/CSAT, churn, repeat rate, and service "
            "recovery. Show the math for every claim."
        ),
        origin_session="20261001_223906_650b71",
        tags=("operations", "cx", "retention"),
    ),
)

DEPARTMENTS: tuple[str, ...] = (CEO_AGENT, CTO_AGENT, COO_AGENT)


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------


def get(name: str) -> SubagentSpec:
    for spec in SPECS:
        if spec.name == name:
            return spec
    raise KeyError(name)


def by_department(department: str) -> list[SubagentSpec]:
    return [s for s in SPECS if s.department == department]


def build_tasks(
    department: str | None = None,
    names: Iterable[str] | None = None,
) -> list[dict]:
    """Return `delegate_task(tasks=...)` entries.

    department: one of DEPARTMENTS, or None for all.
    names:       explicit subagent names (overrides department).
    """
    if names:
        selected = [get(n) for n in names]
    elif department:
        if department not in DEPARTMENTS:
            raise KeyError(f"unknown department: {department}")
        selected = by_department(department)
    else:
        selected = list(SPECS)
    return [s.to_task() for s in selected]


def list_subagents() -> str:
    width = max(len(s.name) for s in SPECS)
    lines = [f"{'SUBAGENT'.ljust(width)}  DEPARTMENT  TAGS"]
    for spec in SPECS:
        lines.append(
            f"{spec.name.ljust(width)}  {spec.department.ljust(10)}  "
            f"{', '.join(spec.tags)}"
        )
    lines.append(f"\n{len(SPECS)} subagents across {len(DEPARTMENTS)} departments.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    arg = sys.argv[1] if len(sys.argv) > 1 else "list"
    if arg == "list":
        print(list_subagents())
    else:
        print(json.dumps(build_tasks(arg), indent=2))
