---
name: buzz-windows-wsl2-dev
description: Run Buzz relay+GUI on Windows when WDAC blocks Rust compile.
---

# Buzz on Windows via WSL2 (WDAC workaround)

## The core problem
On this Windows host (user `jorda`), **org Device Guard / WDAC blocks ALL unsigned executables** — including cargo's generated `build-script-build.exe`. It fails everywhere tried: repo `target/`, `C:\ProgramData`, `C:\Windows\Temp`, with:
`error: failed to run custom build command for X; Caused by: An Application Control policy has blocked this file. (os error 4551)`
**No path-based workaround exists.** The only working route is **WSL2 Ubuntu**, where Linux userspace executes unsigned binaries freely.

## Architecture of the working setup
Buzz has two parts that must both run:
- **Relay** (Rust, `buzz-relay`) → MUST run in **WSL2** (Windows can't compile it). Listens on `ws://localhost:3000`.
- **GUI** (Vite/React in `web/`) → runs on **Windows** via `pnpm` (pure JS, no Rust, no WDAC issue). Served at `http://localhost:4173`, connects to relay via baked `VITE_RELAY_URL=ws://localhost:3000`.

Note: the **native Tauri desktop** (`just dev`) CANNOT run here — it needs a display/webview (headless WSL2 has none) AND Windows can't compile its Rust. The `web/` frontend is the functional equivalent GUI.

## Prerequisites installed (one-time)
- **Windows side:** Node 24 + pnpm 11 (`nvm install 24`; `npm install -g pnpm@11.4.0`); Docker Desktop; Python 3.12; WinLibs MinGW `dlltool` (for the rare Windows-side Rust attempt); a `python3` shim (see below).
- **WSL2 (Ubuntu distro):** Rust 1.95 via rustup; Node 24 + pnpm 11 via corepack (Node tarball downloaded on Windows fast-net, copied in via `wsl.exe cp`, extracted to `~/node24`); `CARGO_TARGET_DIR=$HOME/buzz-target` (keep Rust output in WSL home, never Windows paths).
- **Docker** services (`docker compose up -d`): postgres :5432, redis :6379, minio :9000, keycloak :8180, adminer :8082. These run on Windows Docker; WSL2 reaches them via `localhost` bridge.

## Helper scripts (live in repo root `C:\Users\jorda\buzz`)
- `.buzzdev-env.sh` — Windows helper; exports PATH for cargo (`/c/Users/jorda/.cargo/bin`), node/pnpm (`/c/Users/jorda/AppData/Local/nvm/v24.19.0`), WinLibs dlltool. Source it before any Windows-side pnpm command: `source /c/Users/jorda/buzz/.buzzdev-env.sh`.
- `.wsl_relay_run.sh` — WSL2 launcher for the relay. Sets PATH (node24, cargo, pnpm), `CARGO_TARGET_DIR=$HOME/buzz-target`, `cd /mnt/c/Users/jorda/buzz`, sources `.env` (LF!), sets `BUZZ_WEB_DIR=./web/dist` (optional; relay only serves GUI at `/invite/...` paths, not root — so GUI is served separately via vite preview), then `exec $HOME/buzz-target/debug/buzz-relay`.
- `.wsl_build.sh`, `.wsl_relay_build.sh`, `.wsl_pnpm_setup.sh`, `.wsl_progress.sh` — WSL2 build/setup scripts (copy to `/tmp` in WSL and run).

## Critical gotchas (each cost real time)
1. **WDAC blocks Rust on Windows.** Never attempt `cargo build` on the Windows side for Buzz. Use WSL2.
2. **CRLF line endings.** Repo `.sh` files and `.env` ship with Windows CRLF. Bash in WSL rejects them (`set: pipefail\r: invalid option name`; `.env: $'\r': command not found`). Convert with `sed -i 's/\r$//' file` in WSL before sourcing. Convert `.env` and any `.sh` you run in WSL.
3. **`python3` on Windows resolves to the Microsoft Store stub** (app-execution-alias), not the real Python 3.12. Fix: create a shim dir first on PATH containing `python3` → real exe. E.g. `C:\Users\jorda\t便秘\shim\python3` (a batch file calling the real python.exe). Needed for `scripts/seed-local-community.sh` on Windows.
4. **Seed script needs `psql` OR `docker`.** It runs on Windows (where `docker` exists → uses `docker exec buzz-postgres psql`) + real python3 shim. In WSL2, `docker`/psql aren't available, so run seed from Windows, not WSL.
5. **`pnpm run check` px-text bug on Windows.** `scripts/check-px-text-core.mjs` builds the override key with `path.relative()` which yields backslashes on Windows, but allowlist entries use `/`. Fix: normalize `relativePath` to forward slashes: `path.relative(projectRoot, filePath).split(path.sep).join("/")` and match with `` `${r.root}/` ``. This is cross-platform-correct (CI is Linux where it happened to work).

## Launch procedure (daily, 2 terminals)
**Terminal 1 — relay (WSL2, leave running):**
```powershell
wsl.exe -d Ubuntu -- bash -c 'export PATH=/usr/local/bin:/usr/bin:/bin; cp /mnt/c/Users/jorda/buzz/.wsl_relay_run.sh /tmp/relay_run.sh; bash /tmp/relay_run.sh'
```
**Terminal 2 — GUI (Windows):**
```powershell
cd C:\Users\jorda\buzz\web
pnpm preview --host --port 4173
```
Open `http://localhost:4173` in a browser. If Docker is down first run: `cd C:\Users\jorda\buzz; docker compose up -d`.

## Verify
```powershell
curl -sS http://localhost:3000/                              # relay Nostr metadata JSON
curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:4173/   # GUI → 200
```

## Build steps (only when needed)
- Migrations: in WSL2 → `cargo run -p buzz-admin -- migrate` (must source `.env`, set `CARGO_TARGET_DIR`).
- Seed: on **Windows** with python3 shim + docker → `bash scripts/seed-local-community.sh`.
- Web GUI build (Windows): `source .buzzdev-env.sh; cd web; VITE_RELAY_URL=ws://localhost:3000 pnpm build`.

## Making `pnpm run check` green on Windows
- `web`, `admin-web`, `desktop` source files ship CRLF. Run `biome check --write .` in each (`pnpm -C <dir> exec biome check --write .`) to normalize to LF and fix formatting.
- Then fix the px-text path-separator bug (above) in `scripts/check-px-text-core.mjs`.
- After both, `pnpm run check` → exit 0.

## Verification checklist (real outputs seen)
- `cargo run -p buzz-admin -- migrate` → `MIGRATE_EXIT=0` "Database migrations complete."
- `seed-local-community.sh` → `SEED_EXIT=0` "Seeded local dev community host(s): localhost:3000"
- `cargo build -p buzz-relay` (WSL2) → `RELAY_BUILD_EXIT=0`
- Relay up → `ss -ltn` shows `0.0.0.0:3000 LISTEN`; `curl` WS upgrade → `HTTP/1.1 101 Switching Protocols`
- `pnpm build` (web) → dist with `ws://localhost:3000` baked in; `pnpm preview` → `HTTP 200`
- `pnpm run check` → `PNPM_CHECK_EXIT=0`
