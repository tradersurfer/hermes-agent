"""Contract tests for the CEO department-subagent engine.

Stdlib + pytest only. Asserts relationships (registry covers the session's
subagents, every department round-trips, payloads match the delegate_task
shape), never a frozen snapshot of the goal text.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_DIR = REPO_ROOT / "profiles" / "ceo-agent" / "departments-subagents"
if not ENGINE_DIR.is_dir():
    pytest.skip(f"department subagent engine not installed at {ENGINE_DIR}", allow_module_level=True)
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

import engine  # noqa: E402
import registry  # noqa: E402


def test_registry_and_departments_agree():
    assert {s.department for s in registry.SPECS} == set(registry.DEPARTMENTS)
    for dept in registry.DEPARTMENTS:
        assert registry.by_department(dept), f"{dept} has no subagents"


def test_names_are_unique():
    names = [s.name for s in registry.SPECS]
    assert len(names) == len(set(names))


def test_goals_are_nonempty_and_single_prompt():
    for spec in registry.SPECS:
        assert spec.goal.strip()
        # A goal is one instruction, not a batch: it must not carry the
        # delegate_task "tasks:" envelope that would re-spawn sub-subagents.
        assert '"tasks"' not in spec.goal
        assert spec.role == "leaf"


def test_dispatch_plan_is_delegate_task_shaped():
    plan = engine.dispatch_plan()
    assert plan["tool"] == "delegate_task"
    tasks = plan["arguments"]["tasks"]
    assert len(tasks) == len(registry.SPECS)
    assert len(plan["roster"]) == len(registry.SPECS)
    for task in tasks:
        assert task["goal"].strip()
        # toolsets/model are optional and only appear when the spec pins them
        assert set(task) <= {"goal", "context", "toolsets", "model"}
    # roster order and task order must line up 1:1
    for task, entry in zip(tasks, plan["roster"]):
        assert task["goal"] == entry["goal"]


def test_department_plan_is_a_subset_of_the_full_plan():
    full = {t["goal"] for t in engine.dispatch_plan()["arguments"]["tasks"]}
    for dept in registry.DEPARTMENTS:
        sub = engine.dispatch_plan(dept)["arguments"]["tasks"]
        assert sub
        assert {t["goal"] for t in sub} <= full


def test_explicit_names_select_exactly_those_specs():
    picked = ["crm-data-lead", "field-operations-analyst"]
    plan = engine.dispatch_plan(names=picked)
    assert [r["name"] for r in plan["roster"]] == picked


def test_unknown_department_raises():
    with pytest.raises(KeyError):
        engine.dispatch_plan("marketing-department")
    with pytest.raises(KeyError):
        registry.get("no-such-subagent")


def test_instructions_name_every_subagent():
    plan = engine.dispatch_plan("cto-agent")
    for entry in plan["roster"]:
        assert entry["name"] in plan["instructions"]


def test_runner_service_defers_import_until_used():
    # Constructing the runner must not require an active Hermes turn.
    runner = engine.DepartmentRunner(service=object())
    assert runner._handles == {}


def test_runner_launch_wraps_service_errors():
    class Boom:
        def launch(self, request):
            raise RuntimeError("No active Hermes parent session is available.")

    runner = engine.DepartmentRunner(service=Boom())
    with pytest.raises(engine.SubagentLaunchError) as exc:
        runner.launch(registry.get("strategy-analyst"))
    assert "strategy-analyst" in str(exc.value)


def test_runner_launch_all_collects_failures_per_subagent():
    class Boom:
        def launch(self, request):
            raise RuntimeError("no parent turn")

    runner = engine.DepartmentRunner(service=Boom())
    out = runner.launch_all("coo-agent")
    assert out["launched"] == {}
    assert set(out["failed"]) == {
        "field-operations-analyst",
        "dispatch-scheduling-analyst",
        "sop-process-analyst",
        "customer-experience-analyst",
    }


def test_subagent_launch_request_is_accessible_from_engine():
    """SubagentLaunchRequest must be importable from engine so __init__ can re-export it.

    Regression guard for the bug where __init__.py listed SubagentLaunchRequest
    in __all__ but never imported it from engine.
    """
    assert hasattr(engine, "SubagentLaunchRequest")
