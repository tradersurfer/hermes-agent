---
name: acp-agent-wiring
description: Wire an external AI agent into Buzz via ACP — setup/debug.
---

# Wiring an external agent into Buzz (ACP)

Buzz agents are external processes speaking **ACP (JSON-RPC 2.0 over ndjson stdio)**, spawned by the `buzz-acp` harness. This skill covers building an adapter for any Node/CLI agent and debugging the live loop.

## Wire contract (verified from buzz-acp source)
Harness spawns `agent_command + agent_args`, pipes stdio, injects `BUZZ_RELAY_URL`, `BUZZ_PRIVATE_KEY`, `BUZZ_AUTH_TAG` env. Protocol:
- `initialize` → reply `{protocolVersion:2, agentCapabilities:{loadSession:false,promptCapabilities:{}}, authMethods:[]}`
- `session/new` → reply `{sessionId}` (any string)
- `session/prompt` params `{sessionId, prompt:[{type:"text",text}]}` → stream `session/update` notifications with `update.sessionUpdate:"agent_message_chunk"`, `update.content:{type:"text",text}` → finish by replying `{stopReason:"end_turn"}`
- Unknown method with id → JSON-RPC `-32601`. Reply promptly to initialize — a slow require chain delays boot but works.

## Adapter pattern (see ceo-agent's working adapter)
`C:\Projects\ceo-agent-public\acp\acp-agent.js` — readline on stdin, single dispatch loop, reuses the host app's server-side seam (`lib/ceoAgentServer.js`: cached runtime, provider clients, model resolution) rather than reimplementing routing. Mirror the host app's own turn endpoint (`app/api/chat/route.ts` there) for exact behavior.

## Setup sequence for a new agent
1. Mint identity: `buzz-admin generate-key` (save nsec; set as `BUZZ_PRIVATE_KEY`)
2. Relay membership: `buzz-admin add-member --pubkey <hex> --role member`
3. Channel membership: insert into `channel_members` (cast role `'member'::member_role`) for open channels
4. Emit channel metadata events so Desktop sees them: `buzz-admin reconcile-channels`
5. Name it: `buzz users set-profile --name "X"` with agent key
6. Launch harness (ONE instance only)

## Harness launch
```
buzz-acp --relay-url ws://localhost:3000 --private-key <nsec-hex> \
  --agent-command $(command -v node) --agent-args /path/to/acp-agent.js \
  --subscribe all --respond-to anyone
```
`--subscribe mentions` requires proper pubkey p-tags in messages; `all` responds to any message in member channels (safer start). `.env` sets its own RUST_LOG — export your own AFTER sourcing it.

## Debugging a silent agent (checklist in order)
1. Harness process alive? Only one instance? (duplicate identity → relay kills new one, child dies with EPIPE)
2. Log shows `discovered N channel(s)` + per-channel subscribe? No → restart after membership fixes (boot-time discovery only).
3. Send test message via CLI as another seed key; watch log for `agent_claimed` → `session created` → `turn complete`.
4. Turn completes but no reply visible? Grep log for model errors — OpenRouter `401 User not found` = invalid key; test key directly against `/v1/chat/completions`.
5. Desktop shows no channels despite DB rows? Run `reconcile-channels`; SQL rows alone don't drive UI.
6. **Relay `/query` returns `result_count: 0` despite DB rows for this agent?** → **Community host mismatch** (see below). This is the #1 cause across sessions.

## Deep-dive: Community host mismatch (the #1 silent-agent trap)

**The symptom:** agents connect, auth succeeds, but `discovered 0 channel(s)` and no replies fire. The relay log shows `/query` returning `result_count: 0` even though the DB has kind:39002 discovery events with the agent's pubkey in `#p`.

**The root cause:** the relay resolves the community from the request **host** byte-for-byte. When the harness connects via `ws://127.0.0.1:3000`, the relay maps that host to a community row in Postgres. If the community was provisioned under a different host string (e.g. `localhost:3000`), the harness lands on an **empty** community — `query_events` filters by `community_id` and finds nothing.

This compounds with the WSL2 IPv6 trap (see buzz-windows-wsl2-dev): WSL2 maps `localhost`→`::1`, but the relay listens on IPv4 `0.0.0.0:3000`. So `ws://localhost:3000` connects via WS happy-eyeballs (IPv4 succeeds) but the harness's **HTTP `/query` side-channel** resolves `localhost`→`::1` → connection refused → `POST /query network error` → harness never dispatches the prompt.

**The fix:**
- Always launch harnesses with `BUZZ_RELAY_URL=ws://127.0.0.1:3000` (IPv4 forces both WS and HTTP to hit the same relay).
- Ensure the DB has a single community row whose `host` matches `127.0.0.1:3000` and whose `id` owns all the event data:
  ```sql
  -- Find which community owns the data:
  SELECT community_id, count(*) FROM events GROUP BY community_id ORDER BY count(*) DESC;
  -- Repoint that community's host (after killing the relay):
  DELETE FROM communities WHERE host IN ('127.0.0.1', 'localhost', '127.0.0.1:3000')
    AND id != '<data_community_id>';  -- keep only the data community
  UPDATE communities SET host='127.0.0.1:3000' WHERE id='<data_community_id>';
  ```
- **Always restart the relay** after community host changes — it caches the host→community mapping at startup.

**Diagnostic query (run while relay is up):**
```sql
-- Verify the agent's pubkey is a channel member under the data community:
SELECT encode(pubkey,'hex') AS pk, count(*) FROM channel_members
  WHERE community_id='<data_community_id>' AND encode(pubkey,'hex') LIKE '<agent_pub_prefix>%'
  GROUP BY encode(pubkey,'hex');
-- Confirm the relay sees the 39002 events for this agent:
SELECT count(*) FROM events WHERE kind=39002 AND community_id='<data_community_id>'
  AND EXISTS (SELECT 1 FROM event_mentions WHERE event_id=events.id AND pubkey_hex='<agent_pub_hex>');
```

## Deep-dive: nsec→pubkey mapping verification

**The trap:** when minting keypairs, the stored nsec may derive to a *different* pubkey than expected (e.g. from a stale or corrupted record). The agent will auth with the derived pubkey, which is NOT in `channel_members` → 0 channels → silent.

**Always verify** the mapping before inserting into `channel_members`:
```bash
# Verify nsec derives to the expected pubkey using nostr-tools:
node -e "const {getPublicKey}=require('nostr-tools'); console.log(getPublicKey('<nsec>'))"
# OR post a throwaway profile event and check the relay log for the auth pubkey:
BUZZ_PRIVATE_KEY=<nsec> BUZZ_RELAY_URL=ws://127.0.0.1:3000 \
  /home/jordan/buzz-target/debug/buzz users set-profile --name "verify"
```

## Adapter pattern: model resolution at startup (not per-turn)

The adapter (`acp-agent.js`) calls `ensureModelsResolved(runtime)` which does a network fetch to the provider (e.g. OpenRouter). If this is called **per-turn**, the first hung fetch poisons all subsequent turns via a cached promise — `runTurn` hangs, the harness times out at 60s, and the circuit opens.

**Correct pattern:** fire model resolution **once at startup** (in `handleInitialize`), cache the boolean result, and never await it in the hot `session/prompt` path. If the cached result is `false`, proceed anyway with the broker's statically-known model and let individual turns degrade gracefully:
```js
let modelsReadyCache = false;
let modelsResolvedStarted = false;
function startModelResolution() {
  if (modelsResolvedStarted) return;
  modelsResolvedStarted = true;
  Promise.race([
    ensureModelsResolved(getRuntime().runtime).then(ok => { modelsReadyCache = ok; }),
    new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 25000)),
  ]).catch(() => { /* keep running; turns use cached broker models */ });
}
// In handleInitialize:   startModelResolution();
// In runTurn: DO NOT call ensureModelsResolved — use modelsReadyCache or skip.
```

## Environment notes (jorda's machine)
Relay runs in WSL2 (WDAC blocks Windows Rust); see skill buzz-windows-wsl2-dev for infra. Community is keyed byte-exact on RELAY_URL — `localhost:3000` ≠ `127.0.0.1:3000` (see community host mismatch deep-dive above). ceo-agent adapter lives at `C:\\Projects\\ceo-agent-public\\acp\\acp-agent.js`, one-command bootstrap launcher at `C:\\Users\\jorda\\buzz\\buzz.bat` → `C:\\Users\\jorda\\buzz\\buzzup.sh` (copied to `/home/jordan/buzzup.sh` in WSL2 each run).

### Running commands in WSL2 from the Windows-side terminal
The git-bash shell this agent uses **cannot** `cd /home/jordan` directly (it's a WSL path). Always wrap with `wsl.exe -d Ubuntu -- bash -c '...'`:
```bash
wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/Users/jorda/buzz && CARGO_TARGET_DIR=/home/jordan/buzz-target BUZZ_RELAY_URL=ws://127.0.0.1:3000 /home/jordan/buzz-target/debug/buzz-acp ...'
```
**WSL2 bash variant-assignment bug:** `A=1; echo $A` returns empty. Never use `export VAR=val` or `VAR=val; cmd` — use **inline env only**: `VAR=val command`. This is why the launcher passes all keys as inline env in the `setsid bash -c "..."` string.

### Process lifecycle
- Use **Hermes tracked background processes** (`terminal(background=true)`) for long-lived relay/agent processes — plain `wsl.exe ... &` kills children when the wsl.exe wrapper returns.
- Only **one** buzz-acp instance per identity at a time — duplicates get killed by the relay's NIP-42 auth (same pubkey → new connection evicts old).
- Kill specific PIDs (`kill <pid>`) rather than `pkill` patterns — pkill can match the wrapper bash shell and self-terminate (auto-approved by smart approval, but still dangerous).
- **`setsid bash -c "... &"` inside `wsl.exe -- bash -c '...'`** does NOT reliably daemonize — the child processes get adopted but the parent wsl.exe wrapper kills them on exit. Instead use `setsid bash -c "exec /path/to/binary"` (with `exec` replacing the bash process) launched via a **Hermes tracked background terminal**, or write the launcher to a temp script and call `setsid bash /tmp/launch.sh </dev/null >log 2>&1 &`.
- **Agent crash cascade**: If the node ACP adapter (`acp-agent.js`) dies during an LLM call (e.g. OpenRouter timeout / 401), buzz-acp reports `agent_returned — respawning` then `all agents dead — exiting`. The relay posts fallback kind-7 reactions (👀💬) but **no text replies** — that's how you diagnose it. Restarting the harness resolves it. Always relaunch after crashes.
- **HTTP 429 from relay**: When agents flood the relay with subscription/reaction events, the relay's rate limiter returns 503/429. This causes additional agent crashes. **Stagger agent launches by 8-10s** to smooth the burst.
- **Bootstrap script**: See `references/buzzup.sh` for the verified one-command startup script (`buzzup.sh`) that kills old instances, starts the relay on `ws://127.0.0.1:3000`, and launches all 7 department agents with staggered 10s delays and per-agent log truncation.
