"""Supervisor for the CEO profile's department subagents.

Two run paths, both reproducing the 2026-10-01 JECI-Gang session exactly:

* ``plan_for()`` / ``dispatch_plan()`` — render the registry into a
  `delegate_task(tasks=[...])` payload plus a human-readable roster. This is
  the path the parent agent uses: one `delegate_task` call, host-owned child
  construction, per-task units, the same concurrency cap as the session.
* ``dispatch()`` — programmatic launch through the public
  `agent.subagent_lifecycle` service, for callers that are already inside an
  agent turn and want to supervise handles (status / wait / result / cancel).

Nothing here imports `tools.delegate_tool`; the lifecycle service is the only
child-construction path and it fails closed outside an active turn.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Sequence

try:  # direct import: this directory itself on sys.path
    from registry import DEPARTMENTS, SPECS, SubagentSpec, by_department, get
except ImportError:  # package import: ``departments-subagents`` loaded from its parent
    from .registry import DEPARTMENTS, SPECS, SubagentSpec, by_department, get


class SubagentLaunchError(RuntimeError):
    """Raised when the lifecycle service refuses a launch."""


# --------------------------------------------------------------------------
# Planning path (no child processes started here)
# --------------------------------------------------------------------------


def plan_for(
    department: str | None = None,
    names: Sequence[str] | None = None,
) -> list[SubagentSpec]:
    """Resolve a department or explicit name list into specs."""
    if names:
        return [get(n) for n in names]
    if department:
        if department not in DEPARTMENTS:
            raise KeyError(f"unknown department: {department}")
        return by_department(department)
    return list(SPECS)


def dispatch_plan(
    department: str | None = None,
    names: Sequence[str] | None = None,
) -> dict:
    """Build the exact call the parent should make.

    Returns::

        {
          "tool": "delegate_task",
          "arguments": {"tasks": [ ... ]},
          "roster": [ {"name", "department", "tags", "goal"} ],
          "instructions": "...",   # paste-ready text for the agent
        }
    """
    specs = plan_for(department, names)
    tasks = []
    roster = []
    for spec in specs:
        task = {"goal": spec.goal}
        if spec.context:
            task["context"] = spec.context
        if spec.toolsets:
            task["toolsets"] = list(spec.toolsets)
        if spec.model:
            task["model"] = spec.model
        tasks.append(task)
        roster.append(
            {
                "name": spec.name,
                "department": spec.department,
                "tags": list(spec.tags),
                "role": spec.role,
                "goal": spec.goal,
            }
        )
    return {
        "tool": "delegate_task",
        "arguments": {"tasks": tasks},
        "roster": roster,
        "instructions": _instructions(specs),
    }


def _instructions(specs: Sequence[SubagentSpec]) -> str:
    lines = [
        f"Dispatch {len(specs)} department subagent(s) with one `delegate_task` "
        "call using the `tasks` array above — one entry per subagent, in roster "
        "order. Each entry is already the exact goal/context the subagent ran "
        "with in the JECI-Gang session. Do not merge or rewrite the goals; if a "
        "subagent needs different scope, pass a follow-up `delegate_task` after "
        "the batch returns.",
        "",
        "Roster:",
    ]
    for spec in specs:
        lines.append(f"- {spec.name} ({spec.department}) — {spec.goal.splitlines()[0]}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Supervisor path (public subagent lifecycle API)
# --------------------------------------------------------------------------


@dataclass
class SubagentLaunchRequest:
    """Local mirror of `agent.subagent_lifecycle.SubagentLaunchRequest`.

    Declared here so callers can import the engine without the Hermes package
    on sys.path; `DepartmentRunner` translates it to the real dataclass.
    """

    goal: str
    context: str | None = None
    role: str = "leaf"
    model: str | None = None
    allowed_toolsets: tuple[str, ...] | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None


class DepartmentRunner:
    """Launch registry subagents and collect their results.

    ``service_factory`` defaults to constructing the public
    `SubagentLifecycleService` against the active turn. It must only be called
    from inside a Hermes agent turn; otherwise launch fails closed with
    `SubagentLifecycleError`.
    """

    def __init__(
        self,
        service: Any | None = None,
        service_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._service = service
        self._service_factory = service_factory
        self._handles: dict[str, Any] = {}

    # -- service ---------------------------------------------------------
    @property
    def service(self) -> Any:
        if self._service is None:
            if self._service_factory is None:
                from agent.subagent_lifecycle import (
                    SubagentLifecycleService,
                    get_active_subagent_parent,
                )

                self._service_factory = lambda: SubagentLifecycleService(
                    get_active_subagent_parent
                )
            self._service = self._service_factory()
        return self._service

    # -- lifecycle -------------------------------------------------------
    def launch(
        self,
        spec: SubagentSpec,
        correlation_id: str | None = None,
    ) -> Any:
        """Launch one registry subagent; returns the serializable handle."""
        from agent.subagent_lifecycle import SubagentLaunchRequest as _Request

        request = _Request(
            goal=spec.goal,
            context=spec.context or None,
            role=spec.role,
            model=spec.model,
            allowed_toolsets=tuple(spec.toolsets) if spec.toolsets else None,
            correlation_id=correlation_id or spec.name,
            metadata={"department": spec.department, "subagent": spec.name},
        )
        try:
            handle = self.service.launch(request)
        except Exception as exc:  # surfaced verbatim; never swallowed
            raise SubagentLaunchError(f"{spec.name}: {exc}") from exc
        self._handles[spec.name] = handle
        return handle

    def launch_all(
        self,
        department: str | None = None,
        names: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        specs = plan_for(department, names)
        launched, failed = {}, {}
        for spec in specs:
            try:
                launched[spec.name] = self.launch(spec)
            except SubagentLaunchError as exc:
                failed[spec.name] = str(exc)
        return {"launched": launched, "failed": failed}

    def status(self, name: str) -> Any:
        return self.service.status(self._handles[name])

    def wait(self, name: str, timeout_seconds: float | None = None) -> Any:
        return self.service.wait(self._handles[name], timeout_seconds=timeout_seconds)

    def result(self, name: str) -> Any:
        return self.service.result(self._handles[name])

    def cancel(self, name: str, reason: str = "cancelled by DepartmentRunner") -> Any:
        return self.service.cancel(self._handles[name], reason=reason)

    def collect(self, timeout_seconds: float | None = None) -> dict[str, Any]:
        """Wait on every launched subagent and return results by name."""
        out: dict[str, Any] = {}
        for name, handle in self._handles.items():
            state = self.service.wait(handle, timeout_seconds=timeout_seconds)
            out[name] = {
                "state": getattr(getattr(state, "state", None), "value", state),
                "timed_out": getattr(state, "timed_out", False),
                "result": self.service.result(handle),
            }
        return out


def dispatch(
    department: str | None = None,
    names: Sequence[str] | None = None,
    runner: DepartmentRunner | None = None,
) -> dict[str, Any]:
    """Launch a whole department (or the full registry) and wait for results."""
    runner = runner or DepartmentRunner()
    launched = runner.launch_all(department, names)
    if launched["failed"]:
        return {"launched": list(launched["launched"]), "failed": launched["failed"]}
    return runner.collect()


if __name__ == "__main__":
    import sys

    arg = sys.argv[1] if len(sys.argv) > 1 else "list"
    if arg == "list":
        for spec in SPECS:
            print(f"{spec.name:32} {spec.department:10} {', '.join(spec.tags)}")
        print(f"\n{len(SPECS)} subagents across {len(DEPARTMENTS)} departments: "
              f"{', '.join(DEPARTMENTS)}")
    elif arg in {"all", "*"}:
        print(json.dumps(dispatch_plan(), indent=2))
    else:
        print(json.dumps(dispatch_plan(arg), indent=2))
