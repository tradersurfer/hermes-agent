# Buzz local dev — end-to-end runbook (WDAC-hostile Windows)

Block's Buzz is a Rust relay + React web frontend + optional Tauri desktop. On a
machine where **WDAC/Device Guard blocks unsigned exes** (cargo build scripts
fail with `os error 4551`), the only way to compile the Rust side is inside
**WSL2 Ubuntu**. The React frontend is pure JS and runs fine on Windows. This
file is the concrete, verified runbook.

## Verified result
- Relay built + ran in WSL2: `ws://localhost:3000` -> `101 Switching Protocols`
  (reachable from both WSL2 and Windows).
- Migrations + seed exit 0.
- Web GUI built with `VITE_RELAY_URL=ws://localhost:3000` and served via
  `vite preview --port 4173` on Windows -> `http://localhost:4173` loads the GUI
  and auto-connects to the relay.

## Prereqs (one-time)
- Docker Desktop installed + WSL2 backend enabled, daemon UP.
- WSL2 Ubuntu distro present (`wsl -l -v` shows `Ubuntu`).
- Toolchain installed INSIDE WSL2 (see SKILL.md "One-time setup"):
  rustup 1.95.0, Node 24 (linux tarball), pnpm 11. Keep
  `CARGO_TARGET_DIR=$HOME/buzz-target` (Linux fs, not `/mnt/c`).
- On Windows: Node 24 + pnpm 11, Python 3.12 (for seed script).

## Commands (verified)
```powershell
# 1) Windows side: start Docker services (docker CLI is NOT in WSL2)
docker compose -f C:\Users\jorda\buzz\docker-compose.yml up -d
#    -> postgres :5432, redis :6379, minio :9000, keycloak :8180, etc.

# 2) WSL2: migrations (compiles workspace, ~13 min first time)
wsl.exe -d Ubuntu -- bash -c 'export PATH=/usr/local/bin:/usr/bin:/bin; cp /mnt/c/Users/jorda/buzz/.wsl_build.sh /tmp/build.sh; bash /tmp/build.sh'
#    .wsl_build.sh: export PATH node/cargo; export CARGO_TARGET_DIR=$HOME/buzz-target;
#    cd /mnt/c/Users/jorda/buzz; source .env; cargo run -p buzz-admin -- migrate

# 3) Windows side: seed (needs python3 + docker; uses docker exec psql fallback)
#    Make `python3` resolve to real Python 3.12 via a shim first on PATH
#    (Microsoft Store stub otherwise shadows it). Then:
bash scripts/seed-local-community.sh   # SEED_EXIT=0

# 4) WSL2: run the relay (serves Nostr API at :3000; does NOT serve GUI at root)
wsl.exe -d Ubuntu -- bash -c 'export PATH=/usr/local/bin:/usr/bin:/bin; cp /mnt/c/Users/jorda/buzz/.wsl_relay_run.sh /tmp/relay_run.sh; bash /tmp/relay_run.sh'
#    .wsl_relay_run.sh: export CARGO_TARGET_DIR=$HOME/buzz-target; cd /mnt/c/Users/jorda/buzz;
#    source .env; exec $HOME/buzz-target/debug/buzz-relay

# 5) Windows side: build + serve the web GUI
cd C:\Users\jorda\buzz\web
VITE_RELAY_URL=ws://localhost:3000 pnpm build          # bakes relay URL into bundle
VITE_RELAY_URL=ws://localhost:3000 pnpm preview --host --port 4173
#    -> open http://localhost:4173 in the browser; GUI connects to ws://localhost:3000
```

## Critical gotchas specific to Buzz
- **`BUZZ_WEB_DIR` does NOT serve the GUI at `/`.** The relay's SPA fallback only
  serves `web/dist` for `/invite/<code>` landing paths and git-web-gui paths
  (when `BUZZ_SERVE_GIT_WEB_GUI=on`). Root `/` is the NIP-11/WebSocket handler.
  So do NOT expect `http://localhost:3000/` to render the app. Instead serve the
  built `web/` separately (step 5) and let it talk to the relay.
- **Web app relay URL is same-origin by default** (`relayWsUrl()` derives
  `ws://window.location.host`). Bake `VITE_RELAY_URL=ws://localhost:3000` at
  build time so the GUI (on :4173) reaches the relay (on :3000). `vite preview`
  serves the already-baked dist, so the env must be set during `pnpm build`,
  not just `preview`.
- **`.env` and shell scripts have CRLF** -> strip with
  `sed -i "s/\r$//" .env scripts/seed-local-community.sh` before running in WSL2.
- **`pnpm run check` fails (pre-existing)** on `web`/`admin-web` biome lint
  (60+12 errors). This is upstream frontend lint, unrelated to the running
  backend, and does NOT block the relay/GUI. Don't chase it unless asked to
  auto-fix (which would modify upstream files).
- **Tauri desktop (`just dev`) cannot run here**: it needs a display/webview
  (headless WSL2 has none -- `DISPLAY=:0` set but no X server) AND Windows-side
  Rust compile (blocked by WDAC). The web frontend (step 5) is the working GUI.

## Restart cheat-sheet (next time)
```powershell
docker compose -f C:\Users\jorda\buzz\docker-compose.yml up -d
wsl.exe -d Ubuntu -- bash -c 'export PATH=/usr/local/bin:/usr/bin:/bin; cp /mnt/c/Users/jorda/buzz/.wsl_relay_run.sh /tmp/relay_run.sh; bash /tmp/relay_run.sh'
cd C:\Users\jorda\buzz\web; VITE_RELAY_URL=ws://localhost:3000 pnpm preview --host --port 4173
```
