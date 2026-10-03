---
name: buzz-acp-agent-integration
description: Wire AI agents into Buzz via its ACP harness; see protocol.
---

# Connecting agents to Buzz via ACP

Buzz agents are external processes speaking **ACP (Agent Client Protocol)** — JSON-RPC 2.0 over newline-delimited JSON on stdio. The `buzz-acp` harness listens for @mentions on the relay, spawns your agent, forwards prompts, and relays streamed replies back to the channel.

```
Buzz relay :3000 ←WS→ buzz-acp ←stdio/ACP→ any agent process
```

Works for any program (goose/codex/claude-code ship adapters; custom agents get a thin JSON-RPC shim). Harness reference: `crates/buzz-acp/src/acp.rs` in block/buzz; minimal built-in agent example: `crates/buzz-agent`.

## Setup sequence (in order)
1. Relay running (`ws://localhost:3000`), Docker services up.
2. Build harness: `cargo build -p buzz-acp -p buzz-cli` (~11 min fresh in WSL2 on WDAC hosts; deps cached after).
3. Mint agent identity: `buzz-admin generate-key` → pubkey + nsec. Each agent needs its OWN keypair.
4. Grant relay membership (starts EMPTY): `buzz-admin add-member --pubkey <hex> --role member` — flag form required; positional arg fails. Requires `BUZZ_RELAY_PRIVATE_KEY` set (dev key `00..01`).
5. Grant channel membership: insert into Postgres `channel_members` (pubkey as `decode(hex,'hex')`; role is the `member_role` enum — cast `'member'::member_role`, `'bot'` may not exist). Seed channels first with `scripts/setup-desktop-test-data.sh`.
6. Launch harness (flags below).

## Harness launch contract
```
buzz-acp --relay-url ws://localhost:3000 \
  --private-key <agent key hex> \
  --agent-command node --agent-args adapter.js \
  --subscribe mentions|all|config \
  --respond-to owner-only|allowlist|anyone|nobody
```
Env equivalents: `BUZZ_PRIVATE_KEY`, `BUZZ_ACP_AGENT_COMMAND/ARGS`, `BUZZ_ACP_SUBSCRIBE`. Harness injects `BUZZ_RELAY_URL`, `BUZZ_PRIVATE_KEY`, `BUZZ_AUTH_TAG` into the spawned agent's env. Idle timeout 900s default; hard turn cap 7200s.

## Wire protocol (what an adapter must implement)
- `initialize` → `{protocolVersion: 2, agentCapabilities:{loadSession:false}, authMethods:[]}`
- `session/new` → `{sessionId:"<id>"}`
- `session/prompt` params `{sessionId, prompt:[{type:"text",text}]}` → stream:
  `{"jsonrpc":"2.0","method":"session/update","params":{"sessionId":...,"update":{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":...}}}}`
  then reply `{stopReason:"end_turn"}`
- `authenticate` → `{}`; unknown methods WITH id → `-32601`.

## Adapter pattern for existing agent codebases
Don't reimplement the agent — reuse its server seam. ceo-agent example: `lib/ceoAgentServer.js` exports `getRuntime`, `ensureModelsResolved`, `buildSystemPrompt`, pre-built provider clients — the same seam its web `/api/chat` route uses. The ACP shim maps prompt → turn function → reply text; one shared cached runtime across sessions is fine. Working adapter: `C:\Projects\ceo-agent-public\acp\acp-agent.js`.

## ceo-agent adapter status (this user's agent)
Working adapter: `C:\Projects\ceo-agent-public\acp\acp-agent.js` — verified end-to-end (threaded replies post cleanly). It drives the server seam (`lib/ceoAgentServer.js`) mirroring `app/api/chat/route.ts`; publishes via buzz CLI per THE publish fact above; strips code fences/prefixes; supports `CEO_DEPARTMENT` env pinning with dept→head-id map (`legal`→`clo-agent`, `operations`→`hermes`, etc.).

Dept keys minted and in `C:\Users\jorda\buzz\.wsl_dept_keys.env.sh`; CEO launcher `.wsl_ceo_agent_run.sh`; full-stack launcher `buzz-stack.sh`.

Upstream ceo-agent test quirks patched locally: UploadStore POSIX test skipped on win32; WorkflowScheduler flaky tick hardened with poll-until-ready. Suite green otherwise (~493+55). Roadmap: ceo-agent needs real tool calling/web search outside Buzz; then connect Hermes itself via ACP or Desktop import.

## Channel discovery internals (why a member agent sees 0 channels)
The harness resolves which channels to subscribe via `discover_channels()` in
`crates/buzz-acp/src/relay.rs` — it does **NOT** read the `channel_members`
table directly. It queries **kind:39002** Nostr events (NIP-29 group
membership) filtered by `#p` tag == the agent's own pubkey, then fetches
kind:39000 metadata for those. Consequences:
- An agent can have DB `channel_members` rows (from SQL inserts or
  `add-member`) AND STILL discover 0 channels, because no kind:39002 event
  carries its pubkey in a `#p` tag. Symptom: log shows
  `discovered 0 channel(s)` → `no channel subscriptions resolved — agent will sit idle`.
- The relay only EMITS kind:39000/39002 discovery events on startup when
  `BUZZ_RECONCILE_CHANNELS=true` is set (see `crates/buzz-relay/src/main.rs`
  ~L549). Without it, even a fresh channel seeded via SQL gets no events and
  members are invisible to discovery.
- `reconcile-channels` (buzz-admin) is idempotent: it SKIPS a channel if a
  kind:39000 event already exists. So deleting only 39002 won't help — you
  must delete BOTH 39000 and 39002, set `BUZZ_RECONCILE_CHANNELS=true`, and
  restart the relay so it re-emits both from current `channel_members`.

Fix recipe (dept/secondary identities added after initial seed):
1. Ensure current memberships exist in `channel_members` (SQL insert or
   `buzz-admin add-member --pubkey <hex> --role member`).
2. `DELETE FROM events WHERE kind IN (39000,39001,39002);` in Postgres.
3. Add `BUZZ_RECONCILE_CHANNELS=true` to relay `.env`.
4. Restart relay → startup reconcile emits 39000+39002 for every open channel,
   with `#p` tags for all current members (incl. dept identities).
5. Verify: `SELECT count(*) FROM events WHERE kind=39002 AND tags::text LIKE '%<pubkey>%';` → >0.
6. Restart the harness(es) — discovery is boot-time only.

Note: `POST /events` (HTTP bridge) rejects kind:39002 with
`restricted: unknown event kind` — you cannot inject discovery events that way;
they must come from the relay's own reconcile. See
`references/dept-discovery-and-silent-hang.md` for the exact commands.

## Agent is ONLINE + discovered channels, but NEVER replies
Symptom in harness log: `presence set to online`, `discovered N channel(s)`,
then on a message: `dispatch_pending dispatched=0 queue_depth=1`, repeated
`reaction add timed out` (kind:7 reactions get HTTP 400 from relay — cosmetic),
and finally `respawn failed: agent initialize failed: Request timeout — agent
did not respond within 60s — circuit re-opened`.

Root cause is almost always the **agent adapter hanging on the first turn**,
not the harness. The harness's 60s init/steer timeout then fires, the ACP
circuit breaker opens, and every later turn is dropped. Instrument the adapter
(`console.error` at each step of the turn handler) to find the hang. The
most common one for ceo-agent-class adapters:
- `ensureModelsResolved(runtime)` → `modelBroker.refreshFromOpenRouter()` →
  `openRouterClient.listModels()` → a `fetch()` to OpenRouter that **hangs
  indefinitely** inside the harness-spawned Node process (WSL2 egress is
  flaky). `ensureModelsResolved` caches its promise, so the first hung call
  poisons ALL subsequent turns. A standalone `listModels()` may succeed
  (timing), masking the bug — don't trust the standalone test.
- Fix: wrap the per-turn `ensureModelsResolved` in a `Promise.race` with a
  ~20s timeout and fall back to the broker's already-cached models:
  ```js
  modelsReady = await Promise.race([
    ensureModelsResolved(runtime),
    new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 20000)),
  ]).catch(() => true); // proceed with cached models; a chat reply does not
                         // require a fresh model catalog
  ```
  This bounds the hang so turns always return.
Other hang points to instrument: `runtime.routeTask` (routing), the LLM
`chatCompletion` call, and `execFileSync(buzz messages send)` in the publish
step (wrong `HOME` → bad buzz path → throws, but that's caught, not a hang).
Full recipe in `references/dept-discovery-and-silent-hang.md`.

## Debugging a silent harness (logs show nothing)
- **`.env` hijacks `RUST_LOG`.** The repo `.env` sets `RUST_LOG=buzz_relay=debug,...` (relay-only crates). If the launch script sources `.env`, it overwrites any `RUST_LOG=info` exported before it — the harness then runs with its own activity invisible. Always `export RUST_LOG="info,buzz_acp=debug,acp=debug"` AFTER `source .env` in the launcher. Verify what the running pid actually has: `tr "\0" "\n" < /proc/<pid>/environ | grep RUST_LOG`.
- **Channel discovery happens once, at boot.** After seeding channels or running `buzz-admin reconcile-channels`, you MUST restart the harness — an instance started before the events existed subscribed to nothing and stays deaf forever (messages reach the DB but the harness never sees them).
- **One harness per agent identity.** Two `buzz-acp` instances on the same private key conflict; the new one dies early and its child adapter crashes with `write EPIPE` (the EPIPE is a symptom of the parent dying, not the bug).
- **First turn is slow (~30s).** The adapter lazily requires the agent runtime during `initialize`; budget idle/timeout accordingly. Subsequent turns are fast.
- **Agent replies with model error**: check the provider key visible to the *adapter* process (`OPENROUTER_API_KEY` etc. from ceo-agent's own `.env`). `401 {"error":"User not found."}` = invalid/expired OpenRouter key, not a Buzz auth problem.

## Pitfalls
- **THE publish fact:** the harness never posts model output. Goose/codex reply via their own shell tools; a thin adapter must parse the `[Context]` block in the first prompt text (`Channel: name (#uuid)`, `--reply-to <64-hex>`) and run `execFileSync($HOME/buzz-target/debug/buzz, ['--format','compact','messages','send','--channel',uuid,'--reply-to',hex,'--content','-'], {input: reply})`. Without this, turns "complete", typing shows, but nothing appears in-channel.
- Child process PATH must include `$HOME/buzz-target/debug` AFTER `source .env` or `buzz` CLI is invisible to the adapter's publishes.
- Strip ```bash fences and `[AgentName]` prefixes from model output before publishing — the harness system prompt tells the model to emit those send commands and it will echo them as text into the posted message.
- SQL inserts into `channel_members` are NOT visible to Desktop clients; channel display requires kind:39000 metadata events — run `buzz-admin reconcile-channels` after seeding, then restart harnesses (discovery is boot-time only).
- Communities are keyed byte-for-byte on relay URL: `localhost:3000` ≠ `127.0.0.1` ≠ `localhost`. All clients + agents must use the identical string or they silently join different communities on one relay.
- Agent profiles: `buzz users set-profile --name/--about` under the agent key so Desktop renders names not hex.
- Department subagents: one keypair + one buzz-acp per dept head; pin routing via env read by the adapter (`CEO_DEPARTMENT=legal`) and map dept→head-id (`legal`→`clo-agent`). Full stack launcher: `C:\Users\jorda\buzz\buzz-stack.sh` (relay → health wait → departments); dept keys `.wsl_dept_keys.env.sh`; dept-only launcher `depts_launch_only.sh`.
- WSL2 VM wedges under heavy compile/load (`Wsl/Service/0x8007274c`): recover via `wsl.exe --shutdown`; `/tmp` is wiped — keep helper scripts in repo (/mnt/c), re-copy after restarts. Cap VM in `%USERPROFILE%\.wslconfig` (`[wsl2] memory=4GB processors=4 swap=8GB`).
- Built-in Buzz agents (Fizz/Honey/Pollen) don't respond? They're wired entirely in Desktop's Agents tab (provider/model config) — unrelated to the ACP pipeline.
- `--subscribe mentions` only fires on events tagging the agent's exact pubkey; if the desktop @-autocomplete won't tag raw pubkeys, use `--subscribe all` + author gating.
- **Relay reconcile gate:** `buzz-admin reconcile-channels` is a NO-OP unless
  `BUZZ_RECONCILE_CHANNELS=true` is set in the relay `.env` — without it the
  relay never emits kind:39000/39002 discovery events, so member agents (added
  via SQL/`add-member` after the initial seed) discover 0 channels and sit
  idle. Set the flag, restart the relay, then restart harnesses. (See the
  "Channel discovery internals" section above.)
- **WSL launch gotchas (jorda host):** (1) Do NOT pipe a background
  `wsl.exe -d Ubuntu -- bash -c '...'` through `| tr -d '\0'` — the drained
  pipe SIGPIPEs/SIGHUPs the harness when the filter exits. Launch tracked
  background procs with no trailing pipe (or use `setsid` inside the script).
  The CEO/dept harnesses that stayed up were launched as tracked bg procs
  without the pipe. (2) WSL bash on this host has broken variable assignment
  (`A=xyz; echo $A` → empty; `export`/`source`/indirect `${!var}` unreliable).
  Write launchers with **inline env only**: `VAR=val VAR2=val command`, never
  `export` then `command`. `depts_launch_only.sh` is the working pattern
  (IFS-split array + inline env + `setsid` detach + 12s stagger).
