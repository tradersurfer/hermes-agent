# CEO Agent on Hermes — Implementation Plan

**Strategy: overlay, don't rename.** Upstream Hermes (MIT, Nous Research) has ~5,200 files that mention "hermes"
(Python package `hermes_cli`, `HERMES_HOME`, state modules, installers). A blind global rename would break imports and
make every upstream merge a conflict. Hermes already exposes three seams built for this, so the fork rebrands through them:

| Layer | Seam used | Status in this PR |
|---|---|---|
| Colors + wording (CLI, TUI, desktop GUI) | `hermes_cli/skin_engine.py` built-in skin `ceo-agent` (violet `#8b5cf6` on near-black, from the ceo-agent app palette) | Done, tested |
| App name, app ID, CLI name | `apps/desktop/product-identity.cjs` variant `ceo` -> "CEO Agent", `com.jeci.ceo-agent`, CLI `ceo-agent` | Done, verified |
| Department org chart | Hermes **profiles** (= your `\departments-subagents`), Bots tab, group rooms via `profile.yaml` `ui_meta` | Done, tested |

Equivalence: `ceo-agent` repo = Hermes home; `departments-subagents/*` = `<home>/profiles/*`.

## What's in the PR
- `ceo-agent/profiles/templates/<id>/` — 9 profiles generated from `registry/agent-registry.json` and each agent's `SOUL.md` + `CONTRACT.md`, plus a generated **Lane guard** (routing to the owning agent) and **Off limits** list.
  ceo, cfo, coo (registry id `hermes`), cto, cmo, chro, clo, sales-intake, onboarding-comms.
- `ceo-agent/scripts/install_ceo_profiles.py` — renders templates into `<home>/profiles/`. Keeps the shipped templates **tenant-blind** (principal/business passed at install). Never overwrites your existing SOUL/config (writes `SOUL.ceo-agent.md` to diff; `--force` backs up to `.bak`). Never touches `.env`/auth.
- `tests/ceo_agent/` — 4 tests (templates complete + tenant-blind, placeholders fully rendered, no-clobber, skin loads). Pass using the repo's own conftest.
- `NOTICE-CEO-AGENT.md` — MIT attribution. `LICENSE` untouched.

## Install / test on your machine
```powershell
git clone https://github.com/tradersurfer/hermes-agent; cd hermes-agent
git checkout -b feat/ceo-agent-rebrand
git apply ..\ceo-agent-hermes\0001-ceo-agent-overlay.patch   # or copy the overlay/ tree over the repo
python ceo-agent\scripts\install_ceo_profiles.py --dry-run --principal "Your Name" --business "Your Co"
python ceo-agent\scripts\install_ceo_profiles.py --principal "Your Name" --business "Your Co" --groups "JECI-Gang Chat,Stress Test Room"
python -m pytest tests\ceo_agent
```
Then set `display.skin: ceo-agent` in the root config.yaml (profiles already get it) and reopen the desktop app's Bots tab.
Desktop branded build: `$env:HERMES_DESKTOP_VARIANT='ceo'` before the desktop build.

## Phases
1. **This PR** — skin, identity, 9 profiles, installer, tests.
2. **Rooms + comms** — pre-seed group rooms and routing prompts (the `@agent` handoff you already use); port `jobs.json` routines into `cron/` per profile.
3. **Distribution** — package each profile with `distribution.yaml` so `hermes profile install <git-url>` works for other users (needs placeholder strategy via `env_requires`).
4. **Deeper rebrand (only if wanted)** — logo/avatars, window icons, installer strings, `update-feed` (currently still points at upstream; disable or repoint before shipping builds).
5. **Port ceo-agent skills** — `SkillRegistry`/`WorkflowRuntime` skills into Hermes skills dirs; keep `off_limits` enforcement at both chokepoints (ADR-009/010) rather than a parallel permission system.

## Open items for you
- **11 subagents:** the repo registry defines **9** (7 C-suite + sales-intake + onboarding-comms). Send the other 2 names (or their repo path) and they become two more template folders. I did not invent them.
- Group room names and which agents sit in each (installer `--groups` currently puts all in the first room).
- Avatars: the prototype uses photo avatars; templates use the `blobatar` shape.
- Upstream sync: keep `upstream` remote; changes are small (2 edited files + new dirs), so merges stay clean.
