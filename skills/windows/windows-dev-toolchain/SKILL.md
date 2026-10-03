---
name: windows-dev-toolchain
description: Fix Rust/Node/Docker git-bash toolchain errors on Windows.
category: windows
---

# Windows Dev Toolchain (git-bash)

Set up and debug a **Rust / Node / Docker** build toolchain from **git-bash on Windows** (the MSYS environment Git for Windows ships). These are the recurring gotchas that block `cargo build`, `npm`/`pnpm`, `docker`, and `curl` when you're driving a Windows dev machine from an agent shell. None of them require editing project source — they're environment setup/troubleshooting fixes.

## When to load this
- `cargo build` fails with `error: error calling dlltool 'dlltool.exe': program not found` (windows-gnu target)
- rustup install fails: `download of .../rustup-init.exe ... write of 16384 bytes` / `curl: (23) client returned ERROR on write`
- `curl -o /tmp/file ...` fails with `curl: (23) client returned ERROR on write of N bytes`
- `nvm use 24` reports success but `node`/`npm` are still `command not found` in the shell
- `python3` opens the Microsoft Store instead of running (it's a stub)
- A repo has `bin/activate-hermit` and `bin/*` files containing `.just-1.46.0.pkg` etc. — these are **Hermit pointer stubs**, inert without Hermit installed

## The fixes

### 1. curl write error (code 23) writing to /tmp
git-bash's `/tmp` is an MSYS path that some curl/toolchain downloads choke on. **Use a Windows-style absolute path** for output files: `curl -sSL -o "C:/Users/<user>/tmp/file" https://...` (forward slashes are fine). Also set `export TMPDIR="C:/Users/<user>/tmp"` before running installers that write temp files.

### 2. rustup internal downloader fails
`sh rustup.sh` downloads `rustup-init.exe` to `$TMPDIR`; if that's `/tmp` (MSYS) it errors with a curl-23 write failure. Fix:
```bash
export TMPDIR="C:/Users/<user>/tmp"   # Windows path, NOT /tmp
unset TEMP TMP
sh rustup.sh -y --default-toolchain 1.95.0 --profile default
```
Then add `C:/Users/<user>/.cargo/bin` to PATH (or `source $HOME/.cargo/env`).

### 3. windows-gnu target needs dlltool.exe
The default Rust target on Windows without VS Build Tools is `x86_64-pc-windows-gnu`, which links via MinGW binutils. If `dlltool.exe` is missing:
- `winget install BrechtSanders.WinLibs.POSIX.UCRT --silent` is **slow/unreliable** (often stalls silently — watch for a UAC prompt it may be waiting on).
- **Better:** download the portable zip directly and extract — no installer, no UAC:
  ```bash
  curl -sSL -o winlibs.zip "https://github.com/brechtsanders/winlibs_mingw/releases/download/16.1.0posix-14.0.0-ucrt-r4/winlibs-x86_64-posix-seh-gcc-16.1.0-mingw-w64ucrt-14.0.0-r4.zip"
  mkdir -p "C:/Users/<user>/AppData/Local/WinLibs/ucrt64"
  cd "C:/Users/<user>/AppData/Local/WinLibs/ucrt64" && unzip -q winlibs.zip
  ```
  Add to PATH: `C:/Users/<user>/AppData/Local/WinLibs/ucrt64/mingw64/bin` (note the **nested** `mingw64/bin`, not the top dir). Verify: `dlltool --version` and `gcc --version`.
- Alternative if you have VS Build Tools: `rustup target add x86_64-pc-windows-msvc` and build with `--target x86_64-pc-windows-msvc`.

### 4. nvm-windows PATH doesn't propagate to git-bash
`nvm use 24` modifies the Windows PATH but the git-bash shell doesn't pick it up. Add the versioned dir explicitly:
```bash
export PATH="/c/Users/<user>/AppData/Local/nvm/v24.19.0:$PATH"
```
(Node lives at `C:/Users/<user>/AppData/Local/nvm/vXX.XX.X/node.exe`.) Install pnpm with **npm**, not corepack — `corepack` is often broken under nvm-windows: `npm install -g pnpm@<pin>` (e.g. `pnpm@11.4.0`).

### 5. python3 is a Microsoft Store stub
`python3 --version` says "Python was not found; run without arguments to install from the Microsoft Store." Fix:
```bash
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
```
Then use the explicit path `C:/Users/<user>/AppData/Local/Programs/Python/Python312/python.exe`, or add that `python.exe` dir to PATH.

### 6. Hermit bin/* stubs are inert
Repos using Hermit (e.g. Block's Buzz) ship `bin/activate-hermit` and `bin/<tool>` files containing a single line like `.just-1.46.0.pkg`. These are **package pointers**, not executables — they only resolve once Hermit is bootstrapped, and the bootstrap script itself often errors under git-bash strict mode (`HERMIT_STATE_DIR_RAW: unbound variable`). Don't call `${REPO}/bin/just`, `bin/cargo`, `bin/node`, etc. Instead install the **real** tools (rustup/cargo, nvm/node, winget pnpm, system `just`) and call them directly, replicating any `scripts/dev-setup.sh` steps by hand (e.g. `docker compose up -d`, `cargo run -p <admin> -- migrate`, `pnpm install`). Keep a `.buzzdev-env.sh` (or similar) that exports the real toolchain PATH so you don't re-type it every call — see the `references/` file for a template.

### 7. git-bash mangles `CARGO_TARGET_DIR` into a double-prefixed path
When you set `CARGO_TARGET_DIR=/c/ProgramData/cargo-target/buzz` (git-bash `/c/` form), cargo **internally converts it to `C:/c/ProgramData/cargo-target/buzz`** — a bogus `C:/c/` double drive prefix. Cargo then writes/executes build scripts at that wrong path, which is NOT the location you intended and is still subject to the same Application Control block (see §8). **Always pass `CARGO_TARGET_DIR` in native Windows form with backslashes:** `export CARGO_TARGET_DIR="C:\\ProgramData\\cargo-target\\buzz"`. Verify the resolved path in cargo's error output (it echoes the exact path it tried).

### 8. WDAC / Device Guard blocks unsigned cargo build-script `.exe` files
**This is the hard blocker for compiling any Rust workspace on a WDAC-enforced Windows machine.** Cargo compiles each crate's `build = "build.rs"` into a `target/.../build/<crate>-<hash>/build-script-build.exe` and **executes** it. Under Windows Defender Application Control (WDAC) with a policy that only allows signed/allowlisted binaries, these **unsigned** build-script executables are blocked everywhere a normal user can write:
- repo `target/` dir → blocked
- `C:\ProgramData\...` → blocked
- `C:\Windows\Temp\...` → blocked

Symptom:
```
error: failed to run custom build command for `serde v1.0.228`
Caused by: could not execute process `C:\...\build\serde-...\build-script-build` (never executed)
Caused by: An Application Control policy has blocked this file. (os error 4551)
```
**Diagnostic to confirm it's WDAC (not a path bug):** a Microsoft-signed exe runs fine from the same dir (`python.exe` works), but any unsigned build-script exe is blocked in every writable location. So it's not about *where* — it's that unsigned binaries can't execute at all. (The `hermes.exe` "blocked by organization's Device Guard policy" message is the same family.)

**What does NOT fix it:** changing the Rust target (gnu→msvc), changing `CARGO_TARGET_DIR` location, or reinstalling toolchains. The `-gnu` target additionally needs `dlltool.exe` (§3), but even after that's fixed you hit the WDAC block on a *different* build script (`quote`, then `serde`, then `thiserror`, etc.) — it's the execution policy, not a specific crate.

**The real fixes (require something outside a non-elevated shell):**
- **WSL2 / Linux build (recommended escape hatch):** compile the Rust workspace inside WSL2 (or any Linux userspace) where the Windows Application Control policy does not apply. `cargo build` runs normally there. This is the most reliable path when the host Windows is WDAC-locked. Check `wsl --list` / `wsl --install` first.
- **WDAC policy exception:** an admin/IT action — add the cargo `target/` directory (or a signing cert) to the CI policy via `New-CIPolicy` / a signed catalog. Not doable from the agent shell.
- **Elevated/admin context:** only if WDAC is relaxed for admins in your org (often it isn't).

**Net:** if you see `os error 4551` / "Application Control policy has blocked this file" on a cargo build script on Windows, stop trying path/toolchain permutations and go to WSL2 or escalate to IT. Don't burn cycles on `CARGO_TARGET_DIR` relocation — it won't help.

## Gotcha: Docker Desktop needs a reboot
`winget install Docker.DockerDesktop` reports success but the daemon stays **DOWN** until you **reboot** (WSL2 backend). After reboot verify with `docker info` (not just `docker --version` — that works even when the daemon is down). Watch for a UAC prompt during install; if it stalls, approve it.

## Verification (show real output, don't assert)
After each fix, run the actual command and read its output before declaring success:
- `cargo --version`, `dlltool --version`, `node --version`, `pnpm --version`, `docker info`
- For a build: run `cargo build -p <crate>` and read the **real** error, not a guess. Note that cargo reports a *dependent* crate's downstream error (e.g. `can't find crate for yoke_derive` from inside `yoke`) and swallows the actual cause — build the named dependency in isolation (`cargo build -p yoke-derive`) to surface the true failure. Hyphen↔underscore: a dependency declared as `yoke-derive` (hyphen) is referenced in code as `yoke_derive` (underscore) — that's normal Rust normalization; a "can't find crate for `yoke_derive`" error means the **dependency wasn't actually built/linked**, not a name mismatch.

See `references/windows-git-bash-quirks.md` for exact error transcripts and the commands that fixed them. `references/wdac-build-blocker.md` is the deep-dive on the Windows Defender Application Control (WDAC) block of unsigned cargo build-script executables — including the diagnostic and the WSL2 escape hatch. `templates/buzzdev-env.sh` is a copy-and-edit PATH helper that wires the real toolchain (rustup cargo, nvm node, npm pnpm, WinLibs dlltool, MSVC target) without the repo's inert Hermit `bin/*` stubs.
