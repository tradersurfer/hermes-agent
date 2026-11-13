# Dept-agent channel discovery & silent-adapter debugging

Concrete recipes for the two hardest ACP-agent failure modes seen on jorda's
Buzz stack. Pair with the matching sections in the umbrella SKILL.md.

## 1. Agent is a channel MEMBER but discovers 0 channels (sits idle)
Harness discovery (`crates/buzz-acp/src/relay.rs::discover_channels`) reads
**kind:39002** events with `#p == agent_pubkey`, not the `channel_members`
table. Relay emits 39000/39002 only at startup when
`BUZZ_RECONCILE_CHANNELS=true` (`crates/buzz-relay/src/main.rs` ~L549).

Repro / verify (Postgres, via `docker exec -e PGPASSWORD=...`):
```sql
-- discovery events carrying the agent pubkey?
SELECT count(*) FROM events
WHERE kind=39002 AND tags::text LIKE '%<agent_pubkey_hex>%';
-- 0  => agent invisible to discovery despite DB membership
```
Fix:
```sql
DELETE FROM events WHERE kind IN (39000,39001,39002);
```
+ add `BUZZ_RECONCILE_CHANNELS=true` to relay `.env`
+ restart relay (startup reconcile re-emits both from current `channel_members`,
  with `#p` tags for all members incl. dept identities)
+ restart harness
`POST /events` rejects kind:39002 (`restricted: unknown event kind`) — cannot
inject discovery events via HTTP; they must come from the relay reconcile.

## 2. Agent ONLINE + discovered channels, but never replies
Log signature:
```
discovered N channel(s)
presence set to online
dispatch_pending dispatched=0 queue_depth=1   (repeats)
reaction add timed out  (kind:7 -> HTTP 400, cosmetic)
respawn failed: agent initialize failed: Request timeout — agent did not respond within 60s — circuit re-opened
```
Almost always the **adapter hangs on the first turn**. Instrument the turn
handler with `console.error('[DBG] step')` at each stage. Typical hang:
`ensureModelsResolved` → `refreshFromOpenRouter` → `listModels()` → `fetch()`
to OpenRouter hangs inside the harness-spawned Node (WSL2 egress flaky). The
promise is cached, so the hang poisons all later turns.

Bounded fix (per-turn):
```js
modelsReady = await Promise.race([
  ensureModelsResolved(runtime),
  new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 20000)),
]).catch(() => true);
```
Standalone `listModels()` may succeed → don't trust the standalone test; the
hang is intermittent inside the spawned process.

## 3. WSL launch gotchas (jorda host)
- Don't pipe `wsl.exe ... | tr -d '\0'` on a BACKGROUND launch — the drained
  pipe SIGPIPEs/SIGHUPs the harness. Launch tracked bg procs with no trailing
  pipe.
- WSL bash assignment is broken: use inline env only (`VAR=val cmd`), never
  `export`/`source`/`${!var}`. Working launcher: `depts_launch_only.sh`
  (IFS-split array + inline env + `setsid` + 12s stagger).
