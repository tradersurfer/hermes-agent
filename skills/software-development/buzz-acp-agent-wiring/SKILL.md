---
name: buzz-acp-agent-wiring
description: Connect ACP agents to a Buzz relay; debug silent harnesses.
---

# Wiring external agents into Buzz via ACP

How to connect any external agent process (e.g. a Node orchestrator) to a Buzz
relay so it appears as a channel member and responds to messages. Verified live
on Buzz desktop v0.5.18 + relay 0.2.0 with a custom ceo-agent adapter.

## Protocol contract (JSON-RPC 2.0, ndjson on stdin/stdout)

The `buzz-acp` harness spawns your command (`--agent-command` + `--agent-args`)
with piped stdio and injects `BUZZ_RELAY_URL`, `BUZZ_PRIVATE_KEY`,
`BUZZ_AUTH_TAG` into its env. Messages it sends:

1. `initialize` → reply `{protocolVersion: 2, agentCapabilities: {loadSession:
   false, promptCapabilities: {}}, authMethods: []}`
2. `session/new` → reply `{sessionId: "<any-string>"}`
3. `session/prompt` params `{sessionId, prompt: [{type:"text", text}]}` →
   stream notifications `session/update` with
   `params.update.sessionUpdate = "agent_message_chunk"` and
   `params.update.content = {type:"text", text}`, then reply
   `{stopReason: "end_turn"}`.
4. `authenticate` → `{}`; unknown methods with an id → error `-32601`
   (silence hangs the harness).

Reference implementations in the repo: `crates/buzz-acp/src/acp.rs` (client
side) and `crates/buzz-agent` (minimal agent). A known-good adapter for a Node
multi-agent project exists at `C:\Projects\ceo-agent-public\acp\acp-agent.js`
(reuses that project's server seam `lib/ceoAgentServer.js` rather than its CLI).

## Identity & membership setup

```bash
buzz-admin generate-key                       # mint agent keypair
export BUZZ_RELAY_PRIVATE_KEY=<relay key>     # required for add-member
buzz-admin add-member --pubkey <hex> --role member
# channel rows alone are NOT enough for clients — emit NIP-29 events:
buzz-admin reconcile-channels                 # emits kind:39000 metadata
# profile so the app shows a name, not hex:
BUZZ_PRIVATE_KEY=<agent nsec/hex> buzz users set-profile --name "CEO Agent" --about "..."
```

`channel_members.role` is a Postgres enum — use `'member'::member_role`;
there is no 'bot' value.

## Channel discovery needs kind:39002 events, NOT just DB rows

The harness `discover_channels()` (`crates/buzz-acp/src/relay.rs`) resolves
channel subscriptions by querying **kind:39002 Nostr events** whose `#p` tag
equals the agent's pubkey — it does NOT read the `channel_members` Postgres
table directly. So an agent can be a DB member of a channel yet still log
`discovered 0 channel(s)` / `no channel subscriptions resolved — agent will sit
idle` if no 39002 event carries its pubkey. Symptom: harness connects, sets
`presence set to online`, then hears nothing.

kind:39002 events are **addressable discovery events signed by the relay
keypair** (`emit_group_discovery_events` in `crates/buzz-relay/src/handlers/
side_effects.rs`). They are emitted:
- on channel creation / membership change via the event pipeline, and
- by the startup reconciler **only when `BUZZ_RECONCILE_CHANNELS=true`**.

Critical reconcile nuances (all verified live):
- The startup reconciler (`reconcile_channel_events`) checks for an existing
  **kind:39000** event; if 39000 exists it SKIPS and emits nothing — even if
  39002 is missing. So to force a re-emit you must delete **39000 AND 39002**
  (and 39001), not just 39002.
- `buzz-admin reconcile-channels` has the same gate: it only emits for channels
  missing 39000. If you deleted only 39002, it reports "0 channels reconciled".
- The relay's REST `POST /events` **rejects kind:39002** with
  `400 restricted: unknown event kind` — you cannot inject discovery events via
  the HTTP API. (In dev mode you can pass `X-Pubkey: <relay pubkey>`, but it
  still rejects 39002, so don't waste time there.)
- The relay's dev keypair is `0000…0001` (pubkey `79be667e…`); the reconciler
  signs discovery events with it.

**Verified fix sequence** (when agents show `discovered 0 channel(s)`):
1. Ensure `.env` has `BUZZ_RECONCILE_CHANNELS=true` (it is OFF by default).
2. Ensure the agent pubkeys are in `channel_members` for each open channel
   (`visibility='open'`), `ON CONFLICT DO NOTHING`.
3. Delete stale discovery events so the reconciler re-emits with the current
   member set: `DELETE FROM events WHERE kind IN (39000,39001,39002);`
4. **Restart the relay** — on boot it reconciles and emits fresh 39000/39002
   reading current `channel_members` (incl. department identities).
5. Verify: `SELECT count(*) FROM events WHERE kind=39002 AND tags::text LIKE
   '%<agent hex>%';` should be >0 (one per channel the agent belongs to).
   **Then confirm the relay actually SERVES them** — a DB row is not enough.
   `buzz-acp`'s discovery queries the relay's `/query` HTTP endpoint, which
   reads the relay's in-memory addressable-event store populated at boot.
   Verified gotcha: after the reconcile + relay restart, query the relay
   directly:
   `curl -sS -X POST http://127.0.0.1:3000/query -H 'Content-Type: application/json' -H 'X-Pubkey: <agent hex>' --data-binary '[{"kinds":[39002]}]'`
   — note the body is a bare **JSON array** `[{...}]`, NOT `{"filters":[{...}]}`
   (the latter returns `invalid filters: invalid type: map, expected a
   sequence`). If this returns `[]` despite DB rows existing, the relay's
   in-memory store wasn't repopulated — re-run the boot with events present
   (delete 39000/39001/39002, ensure `BUZZ_RECONCILE_CHANNELS=true`, restart
   relay, confirm rows reappear, THEN launch harness). The harness startup line
   `discovered N channel(s)` is the only user-facing proof; if it says 0, the
   query returned 0 and the agent will sit idle regardless of DB state.
6. Restart the harness — discovery runs once at boot, so a running harness will
   NOT pick up new events until relaunched.
7. **Disable or ignore kind:7 reactions.** The harness attempts to add a 👀
   reaction as a "working" indicator; the relay rejects kind:7 with HTTP 400
   (`reaction add failed: HTTP error: POST /events returned HTTP 400`). This is
   cosmetic noise, not a failure — don't chase it as the cause of silence.

NOTE: `add-member` (buzz-admin) emits kind:13534 roster events (Redis live
update), not 39002. Use it for live membership; use the reconcile sequence
above for discovery.

## Harness launch (key flags)

```
buzz-acp --relay-url ws://localhost:3000 \
  --private-key <agent key> \
  --agent-command <node or other> --agent-args <adapter script> \
  --subscribe all|mentions|config \
  --respond-to anyone|owner-only|allowlist|nobody \
  --dedup queue|drop        # idle timeout default 900s, max turn 7200s
```

The harness injects only `BUZZ_RELAY_URL` / `BUZZ_PRIVATE_KEY` / `BUZZ_AUTH_TAG`
into the adapter's env. **If the adapter calls an LLM (e.g. via OpenRouter), you
MUST pass the provider key yourself in the launch env** — the harness will NOT
supply it. For the ceo-agent adapter, add `OPENROUTER_API_KEY=<key>` inline.
Without it, `runTurn()` hits `ensureModelsResolved` → returns `no_api_key` and
the turn fails; repeated failures trip the ACP circuit breaker
(`respawn failed: agent initialize failed: Request timeout — agent did not
respond within 60s — circuit re-opened`) and the agent goes permanently deaf.
That timeout is most often caused by (a) the adapter missing a required env var
and crashing on first prompt, or (b) too many cold Node runtimes contending for
CPU at once — stagger launches (see the multi-department lessons below).

Prefer `--subscribe all --respond-to anyone` for local dev: mention encoding
varies by client version and plain-text messages then trigger the agent.

## CRITICAL: relay URL must be IPv4 (ws://127.0.0.1, not localhost)

On WSL2 `localhost` resolves to `::1` (IPv6) but the relay listens on IPv4
`0.0.0.0:3000`. The Rust WS client connects anyway (happy-eyeballs falls back
to IPv4), so the harness reaches `connected to relay` + `presence set to
online` — but the harness's **HTTP `/query` side-channel** (used to resolve
thread context and to run the discovery query) targets `http://localhost:3000`
→ `::1` and gets `Connection refused`. Symptom in the harness log:
`POST /query network error: error sending request for url (http://localhost:3000/query)`
repeatedly, and turns never dispatch (`dispatch_pending dispatched=0
queue_depth=1`). The agent looks alive but never answers.

**Fix:** pass `BUZZ_RELAY_URL=ws://127.0.0.1:3000` to the harness. The harness's
`relay_ws_to_http` converts it to `http://127.0.0.1:3000`, which the relay
serves. Verify: `curl -sS http://127.0.0.1:3000/_readiness` works while
`curl http://localhost:3000/_readiness` may still work for WS-only clients —
the tell is the HTTP `/query` network error in the harness log, not the WS
connection. NOTE this is separate from the "community keyed byte-for-byte on
RELAY_URL" lesson: `127.0.0.1` and `localhost` are *also* different
communities, so pick one and use it consistently for relay boot, harness, and
any `buzz` CLI calls.

## nsec→pubkey mapping MUST be verified, not assumed

A stored "nsec for department X" can derive to a DIFFERENT pubkey than the one
you added to `channel_members`. If discovery events (kind:39002) carry that
*actual* (wrong) pubkey, the agent is not a member of any channel and silently
sits idle (`discovered 0 channel(s)`) — even though everything else looks
correct. Verified live: a nsec `b80fb4aded…` was assumed to map to pubkey
`b80fb4aded…`, but `getPublicKey(nsec)` returned `ff305a61…`, an identity that
was a member of NO channel. The harness reported `pubkey=ff305a61…` in its
startup line — that line is the ground truth, not your notes.

**Rule:** after minting any keypair, verify the mapping before trusting it:
```bash
node -e "const {getPublicKey}=require('nostr-tools'); console.log(getPublicKey('<nsec>'))"
```
Then confirm that exact pubkey is in `channel_members` AND in the kind:39002
`#p` tags. If the harness startup line shows a `pubkey=` different from what
you expect, the nsec you passed resolved to something else — stop and
re-mint/verify rather than debugging discovery.

## Model resolution must run at STARTUP, never per-turn

`ensureModelsResolved` (ceo-agent's `lib/ceoAgentServer.js`) calls
`modelBroker.refreshFromOpenRouter()` → `openRouterClient.listModels()` → a
`fetch()` that can hang on flaky WSL2 egress. If you `await ensureModelsResolved`
**inside** `runTurn`, the first hung call caches a never-resolving promise
(`modelsResolvedPromise`); every subsequent turn awaits the SAME hung promise →
the agent goes permanently deaf from turn 2 onward, and the harness trips the
60s `initialize` timeout / circuit breaker.

**Fix:** call `ensureModelsResolved(runtime)` ONCE at `initialize` (fire and
forget, with a 20–25s `Promise.race` cap), cache the boolean result in a module
variable, and have `runTurn` use the cached value. Never `await` it in the hot
path. Add a graceful fallback: if `getApiModelId` is still empty, fall back to a
known-good model id (e.g. `anthropic/claude-3.5-sonnet`) so the agent can still
answer. Inject an explicit identity block into the system prompt
(`You are the <DEPARTMENT> of the organization…`) so pinned department agents
stay in character.

## Debugging a silent/deaf agent

- **Logging trap: `.env` overrides `RUST_LOG`.** Buzz's `.env` sets
  `RUST_LOG=buzz_relay=debug,...` — if your launch script sources `.env`
  AFTER exporting `RUST_LOG=info`, your value is silently replaced and the
  harness logs nothing (looks like a dead agent when it's fine). Always
  export `RUST_LOG` AFTER `source .env` in the launcher script.
- Harness logs go to stdout/stderr only on activity; run once with
  `RUST_LOG=info` in the foreground and watch for
  `discovered N channel(s)` + one `subscribed to channel <uuid>` line per
  channel. Zero `subscribed` lines = it will never hear anything.
- **Run exactly ONE harness instance per agent identity.** Two buzz-acp
  processes sharing a private key conflict at the relay; the new one dies
  mid-boot and its child adapter crashes with `Error: write EPIPE`
  (unhandled stdout write to closed pipe). Before relaunching:
  `pkill -f buzz-acp; pkill -f <adapter script>`. An EPIPE crash in the
  adapter right after the harness sends `initialize` usually means the
  *harness* died, not the adapter.
- **Channel discovery happens once at boot.** After ANY repair (reconcile,
  membership insert, community fix) you must restart the harness.
- Verify the write path independently: send a message AS the agent with
  `buzz --format compact messages send --channel <id> --content "..."`;
  if accepted, identity/DB are fine and the problem is subscription.
- Check messages actually landed: kind 9 events in Postgres (`events` table).
- Community is keyed byte-for-byte on RELAY_URL — `localhost:3000`,
  `127.0.0.1`, and bare `localhost` are three different communities. Compare
  `SELECT host FROM communities;` against the URL clients actually used before
  assuming data loss.
- Built-in desktop agents (Fizz/Honey/Pollen) staying silent is usually a
  missing provider/API key in the desktop Agents tab — unrelated to ACP wiring.
- **OpenRouter 401 "User not found"** = the key itself is rejected by
  OpenRouter (revoked/typo/wrong account), NOT a loading problem. Test
  definitively with `GET /api/v1/models` (public, always 200) vs
  `POST /chat/completions` (auth required) using the exact loaded key — if
  models returns 200 but completion 401s, the key string is simply invalid.
  Also check `.env` for a UTF-8 BOM on line 1 (`od -c | head`) — Node's
  `trim()` strips it, so it usually isn't the culprit, but rule it out.

## Running multiple department agents (one identity per department)

To stand up several Buzz agents that are each its own Nostr identity (e.g.
CFO/COO/CTO/CMO/CHRO/CLO), run ONE buzz-acp per identity. The shared adapter is
pinned to a department via the `CEO_DEPARTMENT` env var, which routes every turn
to that department's head agent (`DEPARTMENT_HEAD_IDS` map: legal→clo-agent,
finance→cfo-agent, etc.). Add the mapping in the adapter:

```js
const DEPARTMENT_HEAD_IDS = {
  executive: 'ceo_agent', finance: 'cfo-agent', operations: 'hermes',
  technology: 'cto-agent', marketing: 'cmo-agent', people: 'chro-agent',
  legal: 'clo-agent',
};
```

Launcher must be robust on WSL2 — three lessons from a live deploy:

1. **Detach with `setsid`.** Launching buzz-acp with `&` inside a script that
   then exits kills the child when the script's shell terminates (the harness
   connected and set presence online, then vanished). Wrap each launch in
   `setsid bash -c '...' &` (or `nohup ... & disown`) so it survives.
2. **Pass env INLINE, not via export/source.** A WSL bash on this host was
   observed with broken variable assignment (`A=xyz; echo $A` → empty) while
   inline `VAR=val command` worked reliably. So write
   `PATH=... BUZZ_PRIVATE_KEY=<nsec> BUZZ_RELAY_URL=ws://localhost:3000 CEO_DEPARTMENT=finance buzz-acp ...`
   rather than `export` + sourcing a key file. If buzz-acp reports
   `Invalid secret key` despite a correct literal nsec, suspect the value never
   reached the process and switch to inline env.
3. **Stagger launches ~12s.** Six cold Node runtimes loading the full project
   at once contend for CPU and several hit the harness's 60s ACP `initialize`
   timeout. Staggering avoids it.

Keep the department nsecs inline in the launcher (don't source an external key
file — see lesson 2). Mint them once with `buzz-admin generate-key`. A
known-good launcher template lives in `references/multi-department-launch.md`.

## Community-host divergence — the real cause of "discovered 0 channel(s)" with data present

A `discovered 0 channel(s)` where DB rows + 39002 events clearly exist is almost
always a **community-host mismatch**, not a missing in-memory store and not a
stale cache. The relay resolves the request's host to a `communities.id`
(`f0877c8f…` etc.) and `query_events` filters `community_id = <resolved>`. The
relay seeds FOUR community rows on first boot: `localhost`, `127.0.0.1`,
`127.0.0.1:3000`, `localhost:3000` — three of them empty. If the harness
connects via `ws://127.0.0.1:3000` it resolves to the (empty) `127.0.0.1:3000`
row, whose `query_events` returns nothing even though all real events live under
the `localhost:3000` row.

Two layers of the same trap:
1. **IPv6/IPv4:** `localhost`→`::1` but relay listens on IPv4 `0.0.0.0:3000`, so
   the harness's HTTP `/query` fails (Connection refused to `::1`). You fix this
   by switching the harness to `ws://127.0.0.1:3000` — but that moves you to a
   *different, empty* community row (layer 2).
2. **Community-host keying:** `localhost:3000` and `127.0.0.1:3000` are distinct
   `communities` rows. The data is under whichever one was seeded first.

**Decisive fix:** make the host the harness uses (`127.0.0.1:3000`, required for
IPv4 HTTP) point at the community row that owns all the data. Do NOT try to
re-point every table — instead **repoint the community row's `host`** while
keeping its `id`:
```sql
-- run with the relay STOPPED (it keeps writing audit_log rows that block the delete)
UPDATE communities SET host='127.0.0.1:3000'
 WHERE id=(SELECT id FROM communities WHERE host='localhost:3000');
-- drop the now-redundant empty rows (only after relay is stopped):
DELETE FROM communities WHERE host IN ('127.0.0.1','localhost');
```
If the DELETE hits a foreign key (audit_log / users / events / channels still
reference a stray row), clear those specific rows for the stray `community_id`
first (`DELETE FROM audit_log WHERE community_id='<stray>';` etc.) — but NEVER
delete the data row. After this, `ws://127.0.0.1:3000` resolves to the data
community and discovery returns the 39002 events.

### Verification (proven live, 2026-08-27 session)

After the SQL repoint + relay restart:

1. `SELECT host FROM communities;` → one canonical row, `127.0.0.1:3000`, id `f0877c8f…`
2. Harness connects → relay log: `NIP-42 auth successful pubkey=<agent hex>` (correct pubkey, NOT the wrong ff305a61…)
3. Harness `/query` → `result_count: 7` (NOT 0) — the `POST /query network error` is gone
4. Harness startup line: `discovered 7 channel(s)` confirmed in DB (7 channel_memberships for the agent pubkey)
5. Live test: post a message → agent responds with reactions in `events` (kind 7) and/or text (kind 9)
6. If the relay log still shows `POST /query network error: error sending request for url (http://localhost:3000/query)`, the harness is still using localhost — re-launch with `BUZZ_RELAY_URL=ws://127.0.0.1:3000`

**Critical**: The data community must be stable across relay restarts. If the
relay's `.env` has `RELAY_URL=ws://localhost:3000` (not `127.0.0.1:3000`), the
relay will re-create a `localhost:3000` community row on boot. This is harmless
as long as the harness connects via `ws://127.0.0.1:3000` (→ the repointed `127.0.0.1:3000` host → `f0877c8f` data community). To avoid confusion, set `RELAY_URL=ws://127.0.0.1:3000` in `.env` so the relay also keys off `127.0.0.1`.

## OPSEC — redact keys in ALL chat output

When the user is present and keys appear (nsec/npub/pubkey hex, API keys),
**redact them in chat** as `[REDACTED]` (or `[REDACTED_PUBKEY]`). This is an
explicit user instruction from the 2026-08-25 session: the agent had been
echoing real department nsecs into the chat. Keep full keys only in on-disk
files the user owns (e.g. the launcher script), never in chat transcripts. When
showing DB dumps or relay logs that contain hex, pipe through
`sed -E 's/[0-9a-f]{64}/[REDACTED]/g'` before displaying.

## Windows/WSL2 specifics (WDAC host)

Relay, harness, and adapter all run inside WSL2; launch script pattern:
copy script to `/tmp`, run with output redirected to a log file
(`bash /tmp/x.sh > /tmp/x.log 2>&1`) since background sessions show nothing.
Node must be on PATH inside WSL (`~/node24/bin`) for the harness to spawn the
adapter. See the environment-level skill for the WDAC workaround itself.

**Docker port-forwards go stale after a WSL `--shutdown`/`shutdown`.** After any
WSL restart, the relay may fail with `Connection reset by peer (os error 104)`
(Postgres) or the readiness check returns `{"status":"not_ready","redis":false}`
(Redis) even though `docker ps` shows the containers `Up`/`healthy`. The
container is fine; its published port-forward into WSL died. Fix:
`docker restart buzz-postgres buzz-redis` (or whichever service the relay can't
reach), then relaunch the relay. This is independent of the WDAC workaround and
recurs every cold WSL boot — restart the affected Docker services *before*
assuming the relay binary is broken.

## Launcher reference

A known-good multi-department launcher (inline-env, `setsid`, staggered) lives in
`references/multi-department-launch.md` — copy and fill in the minted nsecs.
Condensed, session-proven commands (nsec verification, re-mint, channel insert,
discovery re-emit, the correct `/query` body shape, harness launch, model-res
fix, live E2E test) live in `references/verified-recipes.md`.

**One-command launcher (`buzz.bat`)** at repo root on Windows (wake-up word
"buzz"): ensures Docker Desktop is running (starts it if needed), then calls
`bash /home/jordan/buzzup.sh` in WSL2. Usage from Windows: `buzz.bat`.
Companion `buzzup.sh` in WSL handles container startup + relay + staggered
agent launches. The launcher truncates each agent's log file
(`: > $LOG/acp_${name}.log`) to avoid stale data from prior runs — never
inspect an agent log without confirming the file was freshly written, or
you'll read last session's errors and waste time. Eliminates the fragmented
multi-step boot.

## The publish gap (agent "types" but nothing posts)

The harness does NOT post streamed `agent_message_chunk` text to the channel.
Its injected system prompt tells the *model* to publish via
`buzz messages send --channel <uuid> --reply-to <hex>` — which only works if
the agent process has a real shell/tool loop (goose, codex). A pure
text-in/text-out adapter will show typing indicator + 👀💬 reactions, the turn
completes `end_turn`, but **no message ever lands** (verify: no new kind-9 row
from the agent pubkey in `events`).

Two fixes:
- **Adapter auto-publish ("Option B", verified working):** parse the channel
  UUID (`/Channel:\s*\S+\s*\(#([0-9a-f-]{36})\)/`) and thread root
  (`/--reply-to ([0-9a-f]{64})/`) out of the prompt's `[Context]` block, then
  after generating the reply exec
  `buzz --format compact messages send --channel <uuid> [--reply-to <hex>] --content -`
  with `input: reply` via `execFileSync` (stdin avoids quoting hell; needs
  buzz CLI on the child's PATH — add `$HOME/buzz-target/debug` in the launcher
  AFTER `.env` sourcing).
- Strip before publishing: fenced ```bash blocks (the model echoes the command
  it was told to run), leading `[<AgentName>]` prefix, excess blank lines.

## Adapter template notes

When wrapping an existing Node agent, prefer its server-side seam (cached
runtime, shared provider clients, model resolution — e.g. ceo-agent's
`lib/ceoAgentServer.js` + `/api/chat/route.ts` flow) over driving its CLI:
the CLI's readline loop and console rendering are noise you'd have to parse.
Mirror the route handler's exact sequence (skill dispatch → @target routing →
model resolution → provider call) so behavior matches the project's own web UI.