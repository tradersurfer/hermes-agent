"""Department subagent engine for the CEO agent profile.

Supports two import styles:

* **Direct** (directory on ``sys.path``):
    ``from engine import dispatch_plan``

* **Package** (parent directory on ``sys.path``):
    ``from departments_subagents import dispatch``
"""

try:  # package import: parent dir on sys.path → relative imports resolve
    from .engine import (  # noqa: F401
        DepartmentRunner,
        SubagentLaunchError,
        SubagentLaunchRequest,
        dispatch,
        dispatch_plan,
        plan_for,
    )
    from .registry import (  # noqa: F401
        DEPARTMENTS,
        SPECS,
        SubagentSpec,
        build_tasks,
        by_department,
        get,
        list_subagents,
    )
except ImportError:  # direct import: directory itself on sys.path
    from engine import (  # noqa: F401
        DepartmentRunner,
        SubagentLaunchError,
        SubagentLaunchRequest,
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
