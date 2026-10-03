# Verified recipes & transcripts — Buzz ACP agent wiring

Condensed, session-proven commands. Companion to SKILL.md.

## 1. Verify a nsec→pubkey mapping (do this before trusting ANY stored key)
```bash
node -e "const {getPublicKey}=require('nostr-tools'); console.log(getPublicKey('<nsec>'))"
```
If the printed pubkey differs from what you put in `channel_members` / 39002
tags, the mapping was wrong. The harness startup log line
`buzz-acp starting: ... pubkey=<hex>` is the ground truth — believe it over notes.

## 2. Re-mint a department keypair and capture both halves
```bash
out=$(/home/jordan/buzz-target/debug/buzz-admin generate-key 2>&1)
nsec=$(echo "$out" | sed -n 's/.*Secret key:[[:space:]]*\([0-9a-f]*\).*/\1/p')
pub=$(echo  "$out" | sed -n 's/.*Public key:[[:space:]]*\([0-9a-f]*\).*/\1/p')
echo "${name}|${nsec}|${pub}"
```
Output format: `Public key:  <hex>` / `Secret key:  <hex>`.

## 3. Insert new dept pubkeys into all open channels (WSL/Postgres)
```sql
INSERT INTO channel_members (community_id, channel_id, pubkey, role, invited_by)
SELECT ch.community_id, ch.id, decode(d.pk,'hex'), 'member'::member_role,
       decode('0000...0000','hex')
FROM channels ch
CROSS JOIN (VALUES
 ('<pub1>'),('<pub2>'), ... ) AS d(pk)
WHERE ch.visibility='open'
ON CONFLICT DO NOTHING;
```
Delete stale wrong-key members first:
`DELETE FROM channel_members WHERE encode(pubkey,'hex') IN ('<old1>','<old2>');`

## 4. Force discovery-event re-emit (kind 39000/39001/39002)
```sql
DELETE FROM events WHERE kind IN (39000,39001,39002);
```
Ensure `.env` has `BUZZ_RECONCILE_CHANNELS=true`, then **restart the relay**.
On boot it reconciles and emits fresh events reading current `channel_members`.
Verify DB: `SELECT count(*) FROM events WHERE kind=39002 AND tags::text LIKE '%<pub>%';` → >0.

## 5. Probe the relay's /query for 39002 (correct body shape)
The relay wants a bare JSON array, NOT `{"filters":[...]}`:
```bash
curl -sS -X POST http://127.0.0.1:3000/query \
  -H 'Content-Type: application/json' \
  -H 'X-Pubkey: <agent hex>' \
  --data-binary '[{"kinds":[39002]}]'
```
`{"filters":[{"kinds":[39002]}]}` → `invalid filters: invalid type: map, expected a sequence`.
With `#p` filter: `'[{"kinds":[39002],"#p":["<agent hex>"]}]'`.

## 6. Harness launch (IPv4 URL + inline env + setsid + stagger)
```bash
setsid bash -c "PATH=...:/home/jordan/buzz-target/debug:... CARGO_TARGET_DIR=/home/jordan/buzz-target HOME=/home/jordan BUZZ_PRIVATE_KEY=<nsec> BUZZ_RELAY_URL=ws://127.0.0.1:3000 CEO_DEPARTMENT=legal RUST_LOG=info,buzz_acp=info /home/jordan/buzz-target/debug/buzz-acp --relay-url ws://127.0.0.1:3000 --agent-command /home/jordan/node24/bin/node --agent-args /mnt/c/Projects/ceo-agent-public/acp/acp-agent.js --subscribe all --respond-to anyone >> /home/jordan/buzzlogs/acp_legal.log 2>&1" &
sleep 12   # stagger next launch
```
Inline env only (this WSL bash has broken `A=1; echo $A`). `CEO_DEPARTMENT` omitted for CEO.

## 7. Adapter model-resolution fix (ceo-agent acp-agent.js)
At `initialize`: fire once, cache boolean, never await per-turn:
```js
let modelsReadyCache = false, started = false;
function startModelResolution() {
  if (started) return; started = true;
  const rt = getRuntime(); if (!rt || !rt.runtime) return;
  Promise.race([
    ensureModelsResolved(rt.runtime).then(ok => { modelsReadyCache = ok; }),
    new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 25000)),
  ]).catch(() => {});
}
```
Per-turn: use `modelsReadyCache`; if `getApiModelId` empty, fall back to
`process.env.CEO_AGENT_FALLBACK_MODEL || 'anthropic/claude-3.5-sonnet'`.

## 8. Live end-to-end test (post as a test user, expect a reply)
```bash
BUZZ_PRIVATE_KEY=<user nsec> BUZZ_RELAY_URL=ws://127.0.0.1:3000 \
  /home/jordan/buzz-target/debug/buzz messages send \
  --channel <channel uuid> --content "To the CLO Agent: what is our NDA clause?"
# then check the thread for a reply from the agent pubkey
```
Confirm with: `SELECT count(*) FROM events WHERE kind=9 AND pubkey=decode('<agent pub>','hex');`

## 9. Fix community-host divergence (the real "discovered 0 channel(s)" cause)

If probe #5 returns `[]` despite DB 39002 rows + correct nsec→pubkey, the
harness's URL resolves to a DIFFERENT (empty) community row than the data.
```sql
-- 1. STOP the relay first (it writes audit_log rows that block the delete)
SELECT host FROM communities;          -- expect localhost, 127.0.0.1, 127.0.0.1:3000, localhost:3000
-- 2. Repoint the DATA community's host to what the harness uses (keep its id):
UPDATE communities SET host='127.0.0.1:3000'
 WHERE id=(SELECT id FROM communities WHERE host='localhost:3000');
-- 3. Drop the now-empty duplicate rows (only with relay stopped; clear FK refs first):
DELETE FROM audit_log WHERE community_id='<stray id>';   -- repeat for users/events if FK blocks
DELETE FROM communities WHERE host IN ('127.0.0.1','localhost');
-- 4. Restart relay. Now ws://127.0.0.1:3000 → data community.
```
Never re-point every table by hand — repointing the community row's `host`
(keeping its `id`) is enough; all child rows follow via FK.

### Live proof (2026-08-27 session)

After the SQL repoint + relay restart:
1. `SELECT host FROM communities;` → only `127.0.0.1:3000` (id `f0877c8f…`)
2. Relay log: `NIP-42 auth successful pubkey=c3b9f7b6…` (correct, not ff305a61…)
3. Relay log: `HTTP bridge request route=/query status=200 result_count=7` (NOT 0)
4. `SELECT COUNT(*) FROM channel_members WHERE encode(pubkey,'hex')='c3b9f7b6…'` → 7
5. Live test: posted a message → agent reacted (kind 7 events in `events` table)

## 10. OPSEC — redact keys before showing anything in chat

`sed -E 's/[0-9a-f]{64}/[REDACTED]/g'` on any DB dump / relay log before display.
User nsecs go in on-disk launcher files only, never echoed into chat.

## 1. Verify a nsec→pubkey mapping (do this before trusting ANY stored key)
