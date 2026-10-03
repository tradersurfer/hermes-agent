---
name: file-organization
description: "Safely tidy a user's real files: survey, move, verify."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [filesystem, cleanup, organization, safety, productivity]
    related_skills: [subagent-driven-development, plan]
---

# File / Folder Organization (Safe Reorg)

## Overview
Tidy a user's real filesystem (Desktop, Downloads, a project folder, a drive) by
grouping items into category folders. This is a DESTRUCTIVE-LOOKING operation on
the user's actual data, so the workflow is built around not losing anything:
survey, propose, get approval, MOVE (never delete), preserve every unique copy,
then verify.

## When to use
- "Organize my desktop / downloads / this folder"
- "Clean up my files" / "sort my projects"
- Any task that moves many user files at once.

## Do NOT use this for
- Code implementation / feature builds. That is `subagent-driven-development`.
  Critically: you should NOT dispatch subagents to move a user's real files —
  execute the moves directly in the controller session so you can verify each
  one landed. (Subagents add risk and lose in-session verification for zero
  benefit on a real filesystem op.) Keep only the structure (a task list + a
  final verification pass = the "spec compliance" gate) and run the moves yourself.

## Core principles
1. **Survey before you touch.** Enumerate everything, by type and size, first.
   You cannot organize what you haven't seen.
2. **Propose, then get approval.** The user owns their file layout. Show the
   destination tree and the two or three decisions with real trade-offs (how
   deep to group; what to do with zips / shortcuts / caches) BEFORE moving.
3. **MOVE, never DELETE.** Group into category folders; never `rm`. If junk must
   be cleared, move it to a `Junk/` / `Review/` folder, or ask.
4. **Preserve every unique copy.** Apparent duplicates are usually NOT identical.
   Hash before collapsing; keep all variants.
5. **No-clobber moves.** Use `mv -n` (or `robocopy /XC /XN /XO`) so a same-named
   destination can never silently overwrite.
6. **Verify the move.** Count integrity + targeted integrity checks (git
   validity, hash distinctness) afterward.

## Workflow
### 1. Survey
```
cd <target>; ls -la
find . -maxdepth 1 -type f | sed 's/.*\.//' | sort | uniq -c   # file types
du -sm */ 2>/dev/null | sort -rn                                 # dir sizes
```
Spot the categories (projects, archives, shortcuts, loose source, docs, caches).

### 2. Risk recon (do this before any move)
- **Git repos:** `git -C <dir> rev-parse --show-toplevel` and `du -sh <dir>/.git`.
  An empty root `.git` (0 bytes) is harmless; a real repo must be moved intact.
- **Near-duplicate folders:** hash each candidate and compare:
```
for d in dir "dir (1)" "dir (2)"; do
  find "$d" -type f -not -path '*/.git/*' -not -path '*/node_modules/*' \
    -exec md5sum {} \; | sort | md5sum | cut -d' ' -f1
done
```
  If hashes differ, the copies are DIFFERENT work — keep all of them; do not merge.
- **Edit / WIP copies:** a folder named `*-edit-copy*`, `*-working-on`, `*-copy`
  often holds uncommitted changes not in the sibling git repo. Diff file lists
  before discarding or merging.
- **Hidden / cache dirs:** `.venv`, `.git`, `.npm-cache-*`, `.tmp.*`,
  `node_modules`, `package-lock.json` may be load-bearing for tooling. Confirm
  before moving; never move the active venv out from under a running process.

### 3. Propose + approve
Show the planned destination tree and ask the two real questions:
- How deep to group (categorized buckets vs a single flat `Projects/`).
- What to do with zips / shortcuts / caches (`Archives/`, `Shortcuts/`, leave
  hidden dirs at root, or `Junk/` for later review).

### 4. Execute (move, never delete)
Build destination dirs, then move with no-clobber. On git-bash / Windows a
multi-move script with `set -e` aborts the WHOLE batch on the first error — run
each category batch as its own command so a transient failure on one item
doesn't skip the rest.
```
mkdir -p Projects/<bucket> Archives Shortcuts Loose-Source Docs
mv -n <items...> Projects/<bucket>/
mv -n *.zip Archives/
mv -n *.lnk Shortcuts/
```
- **Windows file lock ("Device or resource busy" / "The process cannot access the
  file"):** almost always a transient lock on a git repo or open file. Retry the
  single `mv` once; if it still fails, mirror with robocopy (do NOT delete the
  source until verified):
```
robocopy "<src>" "<dst>" /E /R:1 /W:1 /NFL /NDL /NJH /NJS
# verify counts match, THEN remove src only with explicit user OK
```

### 5. Verify (the "spec compliance" gate)
```
ls -A <target> | sort                                  # root leftovers as planned?
for b in <buckets>; do echo "$b: $(find Projects/$b -maxdepth 1 -mindepth 1|wc -l)"; done
echo "Archives: $(ls Archives|wc -l)  Shortcuts: $(ls Shortcuts|wc -l)"
```
Targeted integrity (only if those items existed):
- Git repo moved OK: `git -C <moved-repo> rev-parse --is-inside-work-tree` and
  `git -C <moved-repo> log --oneline -1`.
- Distinct copies preserved: re-run the md5 hash loop on the NEW paths; hashes
  must be unchanged from the pre-move values.

## Pitfalls
- **"These N folders are the same thing."** They usually aren't. Hash first.
  Collapsing different work is unrecoverable.
- **"The edit-copy is stale, delete it."** It may hold dozens of unique WIP
  files. Diff before touching.
- **`set -e` on a long move script** skips later batches when one item errors.
  Batch by category, or drop `set -e`.
- **Moving a live `.venv` / open project** → Windows lock errors and broken
  tooling. Confirm nothing is using it; retry handles transient locks.
- **Deleting during a "tidy."** Resist. Move to `Junk/` or ask.
- **Dispatching subagents to move real user files.** Don't — you lose in-session
  verification and add risk for zero benefit.

## Verification checklist (final)
- [ ] Every planned item is at its destination (count match).
- [ ] No destination was overwritten (`mv -n` guarantees this; spot-check risky ones).
- [ ] Git repos still valid; distinct copies still distinct.
- [ ] Intended leftovers (hidden / cache dirs) still at root or as agreed.

Full copy-pasteable command recipes: see `references/safe-move-playbook.md`.
