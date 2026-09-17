# Safe Move Playbook (copy-pasteable recipes)

Commands proven on a Windows Desktop tidy via git-bash/MSYS. Adapt paths.

## 1. Survey a directory
```bash
cd /c/Users/<user>/<target>
ls -la                                            # top-level, with sizes
find . -maxdepth 1 -type f | sed 's/.*\.//' | sort | uniq -c   # file-type histogram
find . -maxdepth 1 -type d | tail -n +2           # subdirs only
# dir sizes (can be slow on huge trees; run in background if needed):
du -sm */ 2>/dev/null | sort -rn
```

## 2. Detect git repos vs junk
```bash
git -C . rev-parse --show-toplevel 2>/dev/null   # is TARGET itself a repo?
du -sh .git 2>/dev/null                          # 0 => empty placeholder, safe to ignore
# per-dir git check:
for d in */; do [ -d "$d.git" ] && echo "$d: GIT ($(git -C "$d" remote get-url origin 2>/dev/null || echo no-remote))"; done
```

## 3. Hash-compare candidate duplicate folders
```bash
# A folder's "content signature" (ignores .git/.git internals & node_modules):
sig() { find "$1" -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -exec md5sum {} \; | sort | md5sum | cut -d' ' -f1; }
sig "parlay-hub-github"
sig "parlay-hub-github (1)"   # DIFFERENT hash => different work, keep both
```
Note: on this tidy, 6 `parlay-hub-github*` copies had 6 DIFFERENT hashes
(562K..723K sizes) — they were NOT duplicates. Preserved all.

## 4. Diff an edit-copy against its git sibling (catch uncommitted WIP)
```bash
cd <edit-copy>; find . -type f -not -path './.git/*' | sed 's#^\./##' | sort > /tmp/edit.txt
cd ../<repo>;    find . -type f -not -path './.git/*' | sed 's#^\./##' | sort > /tmp/repo.txt
comm -23 /tmp/edit.txt /tmp/repo.txt    # files ONLY in the edit-copy (uncommitted WIP)
```
On this tidy: the edit-copy held 88 unique files (timestamped picks +
nested `twizzypickz-main/` project) — would have been lost if merged/deleted.

## 5. Build destinations + move with no-clobber
```bash
mkdir -p Projects/<bucket> Archives Shortcuts Loose-Source Docs
# Run EACH batch as its own command (no set -e across all of them):
mv -n <items...> Projects/<bucket>/
mv -n *.zip Archives/
mv -n *.lnk Shortcuts/
mv -n *.jsx *.mjs Loose-Source/
mv -n *.md *.docx Docs/
```
`mv -n` = no-clobber: never overwrites an existing destination name.

## 6. Windows file lock ("Device or resource busy")
A git repo or open file was momentarily locked. The single `mv` aborted AND
(if you used `set -e`) skipped every later batch. Fix:
- Retry the SAME single `mv` — it succeeded on retry here.
- If still locked, mirror (do NOT delete source yet):
```bash
robocopy "<src>" "<dst>" /E /R:1 /W:1 /NFL /NDL /NJH /NJS
# verify file counts equal, THEN remove src only with explicit user OK
```

## 7. Verify (the gate)
```bash
ls -A <target> | sort                          # leftover root items as planned?
for b in <buckets>; do echo "$b: $(find Projects/$b -maxdepth 1 -mindepth 1|wc -l)"; done
echo "Archives:$(ls Archives|wc -l) Shortcuts:$(ls Shortcuts|wc -l) Loose:$(ls Loose-Source|wc -l) Docs:$(ls Docs|wc -l)"
# Git repo still valid after a locked move:
git -C Projects/<x>/<repo> rev-parse --is-inside-work-tree
git -C Projects/<x>/<repo> log --oneline -1
# Distinct copies still distinct (re-run sig from step 3 on NEW paths):
sig "Projects/parlay/parlay-hub-github (5)"     # must match pre-move value
```
