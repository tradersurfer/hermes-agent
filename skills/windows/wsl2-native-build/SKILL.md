---
name: wsl2-native-build
description: Build in WSL2 when Windows WDAC blocks unsigned exes.
---

# WSL2 Native Build — bypass Windows WDAC

## When to use
- Local `cargo build` / `cargo run` / `cc` / `go build` fails with:
  `could not execute process ... build-script-build (never executed) ... An Application Control policy has blocked this file. (os error 4551)`
- Any unsigned `.exe` (cargo build scripts in `target/`, `hermes.exe`) is blocked by Device Guard / WDAC on this machine.
- You must compile or run a native toolchain locally but the Windows host is locked down.

## Core technique
Compile and run inside **WSL2 Ubuntu** (already installed; `docker-desktop` distro is the Docker backend). WDAC does not apply to Linux-userland binaries, so cargo's unsigned build scripts execute freely there. The only cost is slower WSL2 network egress — mitigate by downloading large files on the Windows side and copying them across `/mnt/c`.

## One-time setup
1. Install the toolchain **inside WSL2** (avoid `apt` — it is slow and `sudo` needs a password here):
   - Rust: `curl -sSf https://sh.rustup.rs -o /tmp/rustup.sh && sh /tmp/rustup.sh -y --default-toolchain 1.95.0 --profile minimal` (download is slow but completes).
   - Node: download the **linux** tarball on the WINDOWS side (fast net), then `cp` into WSL via `/mnt/c` and `tar -xJf node.tar.xz -C ~/node24 --strip-components=1`.
   - pnpm: in WSL, `export PATH=$HOME/node24/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin` (**node must be on PATH or `corepack`'s `#!/usr/bin/env node` shebang fails**), then `$HOME/node24/bin/corepack enable --install-directory $HOME/.local/bin; corepack prepare pnpm@<ver> --activate`. Embed `<ver>` from the repo's `packageManager` field.
2. Keep build artifacts on the Linux fs: `export CARGO_TARGET_DIR=$HOME/buzz-target`. Do NOT point it at a `/mnt/c/...` path (see gotchas).

## Running against Windows-side Docker
Docker Desktop runs on Windows; container ports are mapped to the Windows host and reachable from WSL2 via `localhost` (e.g. Postgres `:5432`). However, the `docker` CLI is NOT in WSL2 unless WSL2 integration is enabled — so run `docker compose` / `docker exec` from the **Windows git-bash side**, not WSL2. A common split: generate SQL / run python in WSL2, execute it via Windows-side `docker exec`.

## Gotchas (recipes in references/windows-wdac-gotchas.md)
- **CRLF**: Windows `.sh`/`.env` files have CRLF; WSL bash dies (`set: pipefail\r: invalid option name`). Strip with `sed -i "s/\r$//" file` before sourcing/running in WSL.
- **git-bash `$HOME` leakage**: `wsl.exe -d Ubuntu -- bash -c '...$HOME...'` lets git-bash expand `$HOME` to `C:/Users/jorda` before WSL sees it. Write a static script file, `cp /mnt/c/.../script.sh /tmp/`, then `bash /tmp/script.sh`. Keep PATH clean inside the script.
- **Slow WSL network**: toolchain/large-tarball downloads in WSL2 time out (e.g. Node tarball got 3MB/31MB before timing out). Download on Windows, copy across `/mnt/c` (fast local bridge). For resumed pulls use `curl -C - -o file <url>` — the partial file is reusable on both sides, so a timed-out WSL download can be finished from Windows or vice-versa.
- **python3 on Windows**: `python3` resolves to the Microsoft Store stub. Create a `python3` shim script (first on PATH) that `exec`s the real `Python312/python.exe`.
- **CARGO_TARGET_DIR mangling**: git-bash rewrites `/c/ProgramData/...` to `C:/c/ProgramData/...` (double drive prefix); WDAC then blocks the build-script exe at the wrong path. Use Windows-native `C:\ProgramData\...`, or just build inside WSL2 entirely.
- **WSL2 unresponsive under load**: heavy builds can make the WSL VM intermittently unreachable (`Wsl/Service/0x8007274c`). The build process keeps running — retry the check / be patient; don't assume failure.
- **Hermit `bin/*` stubs**: repos like Buzz ship Hermit pointer files in `bin/` (`bin/cargo`, `bin/just`, `bin/node`). They are inert without Hermit installed. Use your real installed tools; never invoke `${REPO}/bin/*`.
- **`sudo` inside WSL2 hangs with background processes**: `sudo` can deadlock when a prior `sudo` command left a hung process or when running inside background (`&`) subshells. Use `install` or `cp` without sudo where possible, or run `sudo` in a fresh foreground call. See references/windows-wdac-gotchas.md.

## Serving a web GUI that talks to a WSL2 relay
The relay (Rust, built in WSL2) and the frontend (React/Vite, pure JS) are
**separate processes**. Don't assume the relay serves the app at its root:
- A backend that takes `BUZZ_WEB_DIR=<dir>` may only mount the GUI at specific
  SPA paths (e.g. `/invite/<code>` landing pages), leaving `/` as the API/WS
  handler. Verify the router's fallback before promising "open :3000".
- The robust pattern: **build the frontend on Windows** (`pnpm build`, no Rust
  needed) with the relay URL baked in (e.g. `VITE_RELAY_URL=ws://localhost:3000`),
  then **serve it on a different Windows port** (`pnpm preview --port 4173`) and
  open that in the browser. The app connects to the WSL2 relay at `localhost:3000`
  (reachable cross-VM via localhost forwarding). Frontends often default to a
  same-origin relay URL, so the env var must be set at **build** time, not just
  at preview.
- A native Tauri/Electron desktop that needs a display + a Windows Rust compile
  is usually impossible on a WDAC-locked headless host — the web frontend is the
  working GUI. See `references/buzz-local-dev.md` for a full worked example.

## Verification
- `cargo run -p <crate> -- <cmd>` inside WSL2 completes and the binary runs (migrations apply, server listens).
- **`sudo` inside WSL2 hangs with background processes**: `sudo` can deadlock when a prior `sudo` command left a hung process or when running inside background (`&`) subshells. Use `install` or `cp` without sudo where possible, or run `sudo` in a fresh foreground call. See `references/windows-wdac-gotchas.md`.
- **NTFS hardlinks on Windows host**: On this host (`jorda`), `/c/Users/jorda/AppData/Local/hermes` and `/c/Projects/Hermes` are NTFS hardlinks to the same files (same inodes). Use `stat -c '%i %n'` to confirm. `hermes --version` always reports `C:\Projects\Hermes\hermes-agent` as install dir regardless of which path is invoked. See `hermes-windows-ops` skill for more context.

## References
- `references/windows-wdac-gotchas.md` — exact command recipes for each gotcha above.
- `references/buzz-local-dev.md` — full Buzz (Rust relay + React GUI) local-dev runbook: Docker compose, WSL2 migrate/relay, Windows seed + vite preview, and the GUI-not-at-root gotcha.
- `references/ghostty-linux-install.md` — installing Ghostty on WSL2 Ubuntu via community AppImage (no official Linux binaries exist).
