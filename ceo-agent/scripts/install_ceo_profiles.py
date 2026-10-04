#!/usr/bin/env python3
"""Install the CEO Agent department profiles into a Hermes home.

Non-destructive: existing SOUL.md / config.yaml are never overwritten unless --force
(and then backed up as *.bak). Secrets (.env, auth) are never read or written.
Placeholders ({{PRINCIPAL_NAME}} etc.) are filled here so the shipped templates stay tenant-blind.
"""
from __future__ import annotations
import argparse, json, os, shutil, sys, time
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "profiles" / "templates"
UI_KEY = "hermes-bots"


def default_home() -> Path:
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"])
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "hermes" if local else Path.home() / ".hermes"


def render(text: str, values: dict) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def profile_yaml(meta: dict, groups: list[str]) -> str:
    lines = [f"description: {meta['display']} - {meta['lane']}", "description_auto: false", "ui_meta:",
             f"  {UI_KEY}:", "    shape: blobatar", f"    title: {meta['display']}",
             f"    created: {int(time.time() * 1000)}", f"    color: {meta['color']}", "    custom: true", "    groups:"]
    lines += [f"      - {json.dumps(g)}" for g in groups]
    lines += [f"    group: {json.dumps(groups[0])}", "    pinned: true"]
    return "\n".join(lines) + "\n"


def write(path: Path, content: str, force: bool, log: list) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            log.append(f"  = unchanged {path.name}"); return
        if not force:
            alt = path.with_name(path.stem + ".ceo-agent" + path.suffix)
            alt.write_text(content, encoding="utf-8")
            log.append(f"  ! kept existing {path.name}; wrote {alt.name} for you to diff"); return
        shutil.copy2(path, path.with_name(path.name + ".bak"))
        log.append(f"  ~ replaced {path.name} (backup: {path.name}.bak)")
    else:
        log.append(f"  + created {path.name}")
    path.write_text(content, encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", type=Path, default=None, help="Hermes home (default: $HERMES_HOME, %%LOCALAPPDATA%%\\hermes, ~/.hermes)")
    ap.add_argument("--principal", required=True, help="Name of the human principal, e.g. 'Jane Doe'")
    ap.add_argument("--business", required=True, help="Business context, e.g. 'Acme Co'")
    ap.add_argument("--ceo-name", default="CEO Agent")
    ap.add_argument("--groups", default="Executive Team", help="Comma-separated room names for the Bots tab")
    ap.add_argument("--only", default="", help="Comma-separated profile ids to install (default: all)")
    ap.add_argument("--skin", default="ceo-agent")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    home = a.home or default_home()
    groups = [g.strip() for g in a.groups.split(",") if g.strip()] or ["Executive Team"]
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    log: list[str] = []
    for tdir in sorted(TEMPLATES.iterdir()):
        if not tdir.is_dir() or (only and tdir.name not in only):
            continue
        meta = json.loads((tdir / "meta.json").read_text(encoding="utf-8"))
        values = {"PRINCIPAL_NAME": a.principal, "BUSINESS_CONTEXT": a.business,
                  "CEO_AGENT_NAME": a.ceo_name, "AGENT_NAME": meta["display"]}
        dest = home / "profiles" / tdir.name
        log.append(f"{tdir.name} -> {dest}")
        if a.dry_run:
            continue
        dest.mkdir(parents=True, exist_ok=True)
        write(dest / "SOUL.md", render((tdir / "SOUL.md").read_text(encoding="utf-8"), values), a.force, log)
        write(dest / "profile.yaml", profile_yaml(meta, groups), a.force, log)
        write(dest / "config.yaml", f"display:\n  skin: {a.skin}\n", a.force, log)
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
