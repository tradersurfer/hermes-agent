# ceo-agent ACP adapter — working example

Adapter file: `C:\Projects\ceo-agent-public\acp\acp-agent.js` (Node, no deps).
Verified: standalone handshake AND full live loop through buzz-acp (see below).

## Key design decisions
- **Reuse the server seam, not the CLI.** `bin/chat.js` is readline-interactive; instead require `lib/ceoAgentServer.js` which exports `getRuntime` (cached runtime), `ensureModelsResolved`, `buildSystemPrompt`, and pre-built provider clients (`openRouterClient`, etc.) — identical to what the web `/api/chat` route uses.
- **`process.chdir(repo root)` at startup** — `lib/ceoAgentServer.js` resolves `ROOT = path.resolve(process.cwd())`, so cwd must be the ceo-agent repo when the harness spawns the adapter from elsewhere.
- **One shared runtime across all sessions** (matches web server behavior); sessionId generated locally, sessions map kept only for protocol compliance.
- **Skill dispatch first** (`ceo-core/skillDispatch` — `/skill` or `@skill {json}` syntax), then @department routing via `runtime.routeTask`, then provider call. Mirrors route.ts exactly.
- Reply prefix `[<agentName>]` when routed away from CEO so channel readers see which department answered.

## PUBLISH FIX — Option B (adapter posts the reply) CONFIRMED WORKING
The harness does NOT post streamed chunks to the channel; its system prompt expects the agent to publish via `buzz messages send`. A text-only adapter can't execute commands, so turns ended with "typing…" + 👀/💬 reactions but no message. Fix in adapter (`handleSessionPrompt`):
1. Parse from prompt text: channel UUID via `/Channel:\s*\S+\s*\(#([0-9a-f-]{36})\)/`, reply-to via `/--reply-to ([0-9a-f]{64})/`.
2. After `runTurn`, exec `$HOME/buzz-target/debug/buzz --format compact messages send --channel <uuid> [--reply-to <hex>] --content -` with `input: reply` (stdin avoids shell-quoting), timeout 30s.
3. Requires buzz CLI on the CHILD's PATH (add to launcher AFTER `.env` sourcing).
4. **Strip model output before publishing**: fenced ```bash blocks (model echoes the command it "ran"), leading `[CEO Agent]` prefix, 3+ newlines. Verified clean single-sentence replies land threaded in-channel.

## LIVE LOOP CONFIRMED (2026-08-24)
Harness (`--subscribe all --respond-to anyone`) on message in #general:
```
agent_claimed → dispatch_pending dispatched=1
acp::session: session created: ceo-...-1
Model call failed: OpenRouter completion failed: 401 User not found   ← invalid OPENROUTER_API_KEY in ceo-agent .env
pool::prompt: turn complete: end_turn
```
Claim → ACP session → provider call all fired. Only remaining blocker was the 401 (bad OpenRouter key visible to the adapter). Fix = valid key, restart harness, message again.
Note: first turn is slow (~30s) — the harness's `initialize` blocks while Node requires ceo-agent's runtime; budget timeouts accordingly.

## Launch (WSL2, WDAC host)
Launcher: `C:\Users\jorda\buzz\.wsl_ceo_agent_run.sh` → copied to `/tmp/ceo_acp.sh`.
```bash
# AFTER sourcing buzz .env (which sets its own RUST_LOG — see SKILL.md debugging section):
export RUST_LOG="info,buzz_acp=debug,acp=debug"
buzz-acp --relay-url ws://localhost:3000 \
  --private-key <agent key hex> \
  --agent-command "$HOME/node24/bin/node" \
  --agent-args /mnt/c/Projects/ceo-agent-public/acp/acp-agent.js \
  --subscribe all --respond-to anyone
```
Use `--subscribe all`: desktop v0.5.18 renders raw-pubkey mentions as plain text (no tag event), so `mentions` mode never fires.

## Test handshake without Buzz
```bash
cd /c/Projects/ceo-agent-public
printf '%s\n%s\n%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"session/new","params":{}}' \
 '{"jsonrpc":"2.0","id":3,"method":"session/prompt","params":{"sessionId":"s1","prompt":[{"type":"text","text":"hello"}]}}' \
 | node acp/acp-agent.js
```

## Identity & membership state (community host `localhost:3000`)
- Agent pubkey `a45fedb27671ebb3d1c80deb999023e31f58dc7127c480fef3f9d2a847d4fdd9`; display name "CEO Agent" via `buzz users set-profile`. Relay member + open channels.
- Desktop user jorda `8a902372...4bd6`: relay member + same channels.
- Seed fixtures (Tyler/Alice/Bob/Charlie/seed-agent) kept intentionally — user plans to convert them into the per-department agent identities. Tyler key `3dbaebad...f6c03` (public dev fixture from Justfile) used to send test messages as a human.
- Duplicate seed `#general` (id `9f28288a-...`) DELETED 2026-08-24; surviving channels: general(`adafd400`), random, engineering, agents, watercooler, announcements, Welcome, welcome-everyone, DMs. Channel deletion order matters (FK): `thread_metadata` → `channel_members` → `channels`, all in one transaction; migrate members first.
- Harness must be restarted after channel deletes (boot-time discovery); it then reports "discovered 7 channel(s)".

## Deferred / next steps
1. ~~Publish fix~~ DONE — adapter posts replies itself; clean output verified in-channel.
2. Per-department subagents as separate Buzz identities (own keypair + membership + harness each) — reuse seed pubkeys as planned identities where sensible.
3. MCP exposure for Hermes users: separate later project.
4. Optional upstream patches to ceo-agent repo: skip POSIX permission-bit test on Windows (`UploadStore.test.js`), harden flaky timer test with fake timers (`WorkflowScheduler.test.js`).
