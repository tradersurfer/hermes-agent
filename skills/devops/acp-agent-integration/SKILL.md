---
name: acp-agent-integration
description: Wire external AI agents into Buzz via buzz-acp harness.
---

# Connecting external AI agents to Buzz via ACP

Class-level pattern for wiring any external agent program into the Buzz workspace through `buzz-acp` (Agent Client Protocol over stdio), and debugging when it doesn't respond in-channel.

## Architecture

```
Buzz relay (:3000, WS) ←→ buzz-acp harness ←stdio/ndjson JSON-RPC→ agent process
```

- The harness spawns the agent binary, pipes stdio, injects `BUZZ_RELAY_URL` / `BUZZ_PRIVATE_KEY` / `BUZZ_AUTH_TAG` env vars.
- Source of truth for the wire contract: `crates/buzz-acp/src/acp.rs` in block/buzz. Minimal reference agent at `crates/buzz-agent`.

## Wire contract (what an agent must implement)

ndjson JSON-RPC 2.0 on stdin/stdout:

| Method | Required response |
|---|---|
| `initialize` | `{protocolVersion: 2, agentCapabilities: {...}, authMethods: []}` |
| `session/new` | `{sessionId: "<string>"}` |
| `session/prompt` | Stream `session/update` notifications (`sessionUpdate: "agent_message_chunk"`, `content: {type:"text", text}`), then reply `{stopReason: "end_turn"}` |
| `authenticate` | `{}` is fine |
| unknown w/ id | JSON-RPC `-32601 Method not found` |

Notifications use `{"jsonrpc":"2.0","method":"session/update","params":{sessionId, update:{...}}}`.

## Harness flags (buzz-acp)

- `--agent-command` / `--agent-args` (env: `BUZZ_ACP_AGENT_COMMAND/ARGS`) — what to spawn
- `--subscribe mentions|all|config` — if @mentions don't fire from the desktop, switch to `all`; desktop mention encoding may not tag raw pubkeys
- `--respond-to owner-only|allowlist|anyone|nobody`
- `--relay-url`, `--private-key` (or `BUZZ_RELAY_URL` / `BUZZ_PRIVATE_KEY` env)

## Setup sequence

1. Build harness (Linux/WSL2 on WDAC hosts): `cargo build -p buzz-acp -p buzz-cli` (~11 min cold)
2. Mint identity: `buzz-admin generate-key` → pubkey + nsec
3. Relay membership: export `BUZZ_RELAY_PRIVATE_KEY=<relay signing key>` then `buzz-admin add-member --pubkey <hex> --role member`
4. Channel membership: INSERT into `channel_members` with `'member'::member_role` cast, then **run `buzz-admin reconcile-channels`** — desktop only shows channels that have kind:39000 metadata events ("Reconciled N channels")
5. Profile so it renders as a name: `buzz-cli users set-profile --name "..." --about "..."` (otherwise UI shows raw hex)
6. Launch harness logging to file: `bash run.sh > /tmp/acp_run.log 2>&1`

> **Authoritative, deep version:** see the `buzz-acp-agent-wiring` skill
> (software-development) — it covers the IPv4-URL trap (`ws://127.0.0.1:3000`,
> not `localhost`, or the harness's HTTP `/query` side-channel fails), the
> real root cause of `discovered 0 channel(s)` (community-host divergence
> across the four seeded `communities` rows), nsec→pubkey verification,
> model-resolution-at-startup, the correct `/query` body shape, and OPSEC
> (redact keys in chat). Use that skill for any real wiring/debugging work.

## Two must-do corrections this skill previously under-specified

- **Use `ws://127.0.0.1:3000` (IPv4), never `localhost`.** On WSL2 `localhost`→`::1`
  but the relay listens on IPv4 `0.0.0.0:3000`; the WS connects but the harness's
  HTTP `/query` (used for discovery + thread context) hits `::1` and gets
  Connection refused → agent never dispatches.
- **Verify nsec→pubkey before trusting it.** A stored nsec can derive to a
  DIFFERENT pubkey than you added to `channel_members`/39002 tags → agent is a
  member of no channel → `discovered 0 channel(s)`. Check:
  `node -e "const {getPublicKey}=require('nostr-tools'); console.log(getPublicKey('<nsec>'))"`
  and confirm the harness startup `pubkey=` line matches.
- **OPSEC:** redact nsec/pubkey hex (`sed -E 's/[0-9a-f]{64}/[REDACTED]/g'`) in
  chat output; keep full keys only in on-disk launcher files.

## Debugging checklist (ordered by likelihood)

1. Agent process alive? `ps aux | grep buzz-acp`
2. Channels visible in desktop but no reply → mention didn't fire; restart harness with `--subscribe all`
3. Channels missing entirely → run `buzz-admin reconcile-channels`; raw SQL rows alone are invisible to the desktop
4. Multiple communities confusion → communities are keyed byte-for-byte on join URL (`localhost:3000` ≠ `127.0.0.1` ≠ `localhost`). Check `SELECT host,id FROM communities;`. But don't assume a split — verify which community the user's channels actually live in first
5. Member shows as hex stranger → seeded/test pubkeys have no profile; expected
6. Quiet logs are normal when idle — check the log file only after sending a test message

## Adapter pattern for wrapping an existing agent CLI

Don't reimplement the agent's brain — drive its server/library seam directly:
- Find the internal API the web dashboard uses (e.g., ceo-agent's `lib/ceoAgentServer.js`: cached runtime, provider clients, `ensureModelsResolved`)
- Mirror the web route's turn flow (route → resolve model → chatCompletion) inside `handleSessionPrompt`
- `process.chdir()` to repo root first if library paths resolve against cwd
- Reply format: prefix `[DeptName] ` when routing to a subagent so channel readers know who spoke

Working example: `C:\Projects\ceo-agent-public\acp\acp-agent.js` (Node adapter for ceo-agent, verified end-to-end against buzz-acp).
