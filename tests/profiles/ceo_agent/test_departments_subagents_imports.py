"""Import-surface contract for the department subagent package.

The engine directory name contains a hyphen, so it is only ever loadable as a
module from its parent — these tests pin BOTH import styles end to end, which
is what the earlier `__init__.py` fix missed (it fixed `__all__` but left the
package path unimportable because `engine`/`registry` only did bare imports).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[3] / "profiles" / "ceo-agent" / "departments-subagents"
PARENT_DIR = ENGINE_DIR.parent
MODULE_NAME = ENGINE_DIR.name  # "departments-subagents"


def _run(code: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_package_import_exposes_full_public_surface():
    """Parent dir on sys.path → import the directory as a module."""
    proc = _run(
        "import importlib, sys; sys.path.insert(0, '.');"
        f"m = importlib.import_module({MODULE_NAME!r});"
        "missing = [n for n in m.__all__ if not hasattr(m, n)];"
        "print('MISSING:' + ','.join(missing));"
        "print('SPECS:%d' % len(m.SPECS));"
        "print('TASKS:%d' % len(m.dispatch_plan()['arguments']['tasks']))",
        PARENT_DIR,
    )
    assert proc.returncode == 0, proc.stderr
    assert "MISSING:" in proc.stdout, proc.stdout
    missing = proc.stdout.split("MISSING:")[1].splitlines()[0].strip()
    assert missing == "", f"public surface missing: {missing}"
    assert "SPECS:11" in proc.stdout
    assert "TASKS:11" in proc.stdout


def test_direct_import_still_works_from_engine_dir():
    """Engine dir on sys.path → bare `import engine`."""
    proc = _run(
        "import engine, registry;"
        "print('SPECS:%d' % len(registry.SPECS));"
        "print('TASKS:%d' % len(engine.dispatch_plan()['arguments']['tasks']));"
        "print('LAUNCH_REQ:%s' % hasattr(engine, 'SubagentLaunchRequest'))",
        ENGINE_DIR,
    )
    assert proc.returncode == 0, proc.stderr
    assert "SPECS:11" in proc.stdout
    assert "TASKS:11" in proc.stdout
    assert "LAUNCH_REQ:True" in proc.stdout


def test_package_and_direct_agree_on_registry():
    """Both import paths must expose the same 11 specs, not two copies that drift."""
    pkg = _run(
        "import importlib, sys; sys.path.insert(0, '.');"
        "m = importlib.import_module(%r);"
        "print(','.join(s.name for s in m.SPECS))" % MODULE_NAME,
        PARENT_DIR,
    )
    direct = _run(
        "import registry; print(','.join(s.name for s in registry.SPECS))",
        ENGINE_DIR,
    )
    assert pkg.returncode == 0 and direct.returncode == 0
    assert pkg.stdout.strip() == direct.stdout.strip()
    assert len(pkg.stdout.strip().split(",")) == 11


def test_module_is_importable_without_a_parent_package():
    """No `import departments_subagents` — the hyphen makes that unimportable.

    Pins WHY the loader must use importlib, so nobody 'simplifies' it back.
    """
    proc = _run("import departments_subagents", PARENT_DIR)
    assert proc.returncode != 0
    assert "departments_subagents" in proc.stderr


def test_subagent_launch_request_is_exported_by_package():
    proc = _run(
        "import importlib, sys; sys.path.insert(0, '.');"
        f"e = importlib.import_module({MODULE_NAME!r} + '.engine');"
        "print('OK:%s' % hasattr(e, 'SubagentLaunchRequest'))",
        PARENT_DIR,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK:True" in proc.stdout