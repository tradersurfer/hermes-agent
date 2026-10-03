"""Department subagent engine for the CEO agent profile.

`from departments_subagents import dispatch` is the one-call entry point; the
registry of subagent definitions lives in `registry.py` and the supervisor in
`engine.py`.
"""

from engine import (  # noqa: F401
    DepartmentRunner,
    SubagentLaunchError,
    dispatch,
    dispatch_plan,
    plan_for,
)
from registry import (  # noqa: F401
    DEPARTMENTS,
    SPECS,
    SubagentSpec,
    build_tasks,
    by_department,
    get,
    list_subagents,
)

__all__ = [
    "DEPARTMENTS",
    "SPECS",
    "DepartmentRunner",
    "SubagentLaunchRequest",
    "SubagentLaunchError",
    "SubagentSpec",
    "build_tasks",
    "by_department",
    "dispatch",
    "dispatch_plan",
    "get",
    "list_subagents",
    "plan_for",
]
