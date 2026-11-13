# Session log: ceo-agent Buzz integration (2026-08-24)

## What was built
1. **ACP adapter** `C:\Projects\ceo-agent-public\acp\acp-agent.js`
   - JSON-RPC/ACP over ndjson stdio; drives ceo-agent's server seam (`lib/ceoAgentServer.js`: getRuntime, ensureModelsResolved, buildSystemPrompt, pre-built provider clients) mirroring `app/api/chat/route.ts`.
   - Publishes replies itself via buzz CLI (harness doesn't post model output).
   - Strips ```bash fences and `[CEO Agent]` prefix before publishing.
   - Parses `[Context]` block: `Channel: name (#uuid)` + `--reply-to <hex>` for threading.
   - Supports department pinning via `CEO_DEPARTMENT` env; dept→head map: executive→ceo_agent, finance→cfo-agent, operations→hermes, technology→cto-agent, marketing→cmo-agent, people→chro-agent, legal→clo-agent.

2. **Keys** (minted via `buzz-admin generate-key`, stored in `C:\Users\jorda\buzz\.wsl_dept_keys.env.sh`):
   - CEO: pub a45fedb27671ebb3d1c80deb999023e31f58dc7127c480fef3f9d2a847d4fdd9
   - finance c5cbb72d…, operations 7c85aa46…, technology 714416ec…, marketing e669b972…, people 5504425d…, legal b80fb4ad… (full hex + nsecs in the env file)

3. **Launchers** in repo root:
   - `.wsl_ceo_agent_run.sh` — CEO harness (PATH fix, RUST_LOG after .env)
   - `depts_launch_only.sh` — 6 dept harnesses + profiles + membership
   - `buzz-stack.sh` — full stack: relay → health wait → departments

4. **Cleanup done**: duplicate seed `#general` (9f28288a…) deleted after migrating memberships to user-created general (adafd400…). Test users kept deliberately (future dept agents).

5. **Upstream test patches** (ceo-agent repo):
   - tests/UploadStore.test.js: POSIX permissions test skipped on win32 (NTFS ignores mkdir modes).
   - tests/WorkflowScheduler.test.js: flaky tick test now polls until ≥2 ticks (5s deadline) instead of fixed sleep.

## Debugging journey (condensed)
- Silent replies → found adapter had no tool loop; model echoed `buzz messages send` commands as text instead of executing. Fix = adapter publishes.
- Empty harness logs → repo `.env` overwrote RUST_LOG; export after source.
- Deaf harness → channel discovery is boot-only; reconcile-channels then restart.
- Duplicate communities → relay URL byte-mismatch (localhost vs 127.0.0.1 vs port).
- WSL wedges (0x8007274c) under load → wsl --shutdown recovery; .wslconfig caps added (memory=4GB, swap=8GB); /tmp wiped on shutdown so scripts live on /mnt/c.

## Verification evidence
- Threaded NDA reply rendered clean in Desktop (no code blocks) — user screenshot confirmed.
- DB check: agent kind-9 message at 22:24:57 "Clean-output test acknowledged…" single sentence.
- Test suite: core 493 pass / 0 fail / 1 skip-win32; components 55/55.

## Remaining roadmap (user's plan)
- Fix built-in agents (Fizz etc.) via Desktop Agents tab provider config (user using Nvidia free models via OpenRouter).
- ceo-agent independent improvement: real tool calling, web search/fetch.
- Connect Hermes Agent into Buzz via ACP or Desktop import.
