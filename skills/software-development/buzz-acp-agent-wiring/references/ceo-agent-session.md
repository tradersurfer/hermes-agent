# Session log: ceo-agent → Buzz wiring (2026-08-24)

Concrete values and transcript excerpts from the session that produced the
umbrella skill. Use as a worked example, not a general rule.

## Endpoints & identities used

- Relay: `ws://localhost:3000` (relay 0.2.0, dev keypair pubkey
  `79be667e...` — BUZZ_RELAY_PRIVATE_KEY = 32 hex zeros + `1`)
- Human (desktop): `8a902372577d73530a84937afe63c40512b6cec23393fc793afafb9d034a4bd6` (BitcoinADrian)
- CEO agent: `a45fedb27671ebb3d1c80deb999023e31f58dc7127c480fef3f9d2a847d4fdd9`
  (nsec `290126cd...5de61`, minted via `buzz-admin generate-key`)
- Old npub identity from myNostr: npub1pue3... → hex
  `0f3310873ab1883edb6d11d4b455c5743a0ec93e8dab4b093ce599ad4fa30964`
- Seed test identities from `scripts/setup-desktop-test-data.sh`: Tyler
  `e5ebc6cd...`, Alice `953d3363...`, Bob `bb22a529...`, Charlie `554cef57...`,
  seed agent `db0b028c...`

## Communities table state (the byte-for-byte lesson)

```
localhost      | 6524f8a2-...
127.0.0.1      | cf038050-...
127.0.0.1:3000 | 2e75f344-...
localhost:3000 | f0877c8f-...   <- the real one everything landed in
```

Desktop channels (general/Welcome/welcome-everyone, created by the human)
turned out to be in `localhost:3000` too — an apparent "split community" was
actually one community; verify before assuming.

## Working launch script (.wsl_ceo_agent_run.sh in buzz repo) — CURRENT

```bash
export PATH="$HOME/node24/bin:$HOME/.cargo/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
cd /mnt/c/Users/jorda/buzz; set -a; source .env; set +a
# AFTER source .env — .env sets its own RUST_LOG (buzz_relay=debug,...) which
# silently clobbers any earlier export and hides all harness logging.
export RUST_LOG="info,buzz_acp=debug,acp=debug"
export BUZZ_PRIVATE_KEY="<agent nsec hex>"
# buzz CLI must be on the CHILD's PATH — the adapter publishes replies via it.
export PATH="$HOME/buzz-target/debug:$PATH"
exec "$HOME/buzz-target/debug/buzz-acp" \
  --relay-url ws://localhost:3000 \
  --agent-command "$(command -v node)" \
  --agent-args "/mnt/c/Projects/ceo-agent-public/acp/acp-agent.js" \
  --subscribe all --respond-to anyone
```

Before relaunching always `pkill -f buzz-acp; pkill -f acp-agent.js` — two
harnesses on one identity conflict at the relay; the loser dies mid-boot and
its adapter crashes with an unhandled EPIPE on stdout.

Run pattern under WSL from Windows:
`wsl.exe -d Ubuntu -- bash -c 'cp /mnt/c/Users/jorda/buzz/.wsl_ceo_agent_run.sh /tmp/x.sh; bash /tmp/x.sh > /tmp/acp_run.log 2>&1'`
Log file redirect is essential: background sessions show nothing.

## Healthy-boot log signature (RUST_LOG=info)

```
buzz-acp starting: relay=ws://localhost:3000 pubkey=a45fedb2... subscribe=All ... respond_to=anyone
agent initialized: {"protocolVersion":2,...}
connected to relay at ws://localhost:3000
subscribed to membership notifications
discovered 8 channel(s)
subscribed to channel <uuid>   (x8)
presence set to online
```

The failing instance had none of the `subscribed to channel` lines — it was
booted before `buzz-admin reconcile-channels` emitted kind:39000 events, and
channel discovery happens only at boot.

## CLI syntax gotchas

- Global format flag goes BEFORE subcommand: `buzz --format compact channels list`
- `buzz messages send --channel <id> --content "..."` (`--text` is invalid)
- Profile publish that worked:
  `buzz users set-profile --name "CEO Agent" --about "..."`
- `buzz-admin add-member --pubkey <hex> --role member` needs
  BUZZ_RELAY_PRIVATE_KEY exported or it errors.
- SQL insert needed cast: `'member'::member_role` (role is an enum; 'bot' value
  does not exist).

## Adapter verification handshake

Piping three JSON-RPC lines into `node acp/acp-agent.js` produced initialize
result, sessionId, one agent_message_chunk notification with a real routed
model reply, then `{stopReason:"end_turn"}` — exit 0, empty stderr.

## OpenRouter 401 (RESOLVED later in session)

The adapter pipeline was proven end-to-end except the final model call:
harness claimed the message (`agent_claimed` → `dispatch_pending dispatched=1`
→ session created → `turn complete ... end_turn`) but the reply text was
`Model call failed: OpenRouter completion failed: 401 {"error":{"message":
"User not found.","code":401}}`. The key (ending `bd7d`, 73 chars, clean
bytes, no BOM interference — Node trim strips the file's UTF-8 BOM) failed
identically from WSL node AND Windows node with a bare fetch, so it is
invalid at OpenRouter's side, not an environment problem. Diagnostic
pattern: `GET /api/v1/models` is public (200 either way);
`POST /chat/completions` with the exact loaded key is the real test.
User replaced the key; new key verified with a direct `POST /chat/completions`
(200 + completion body) BEFORE restarting the harness — restart harness after
any `.env` key change so the adapter's lazy-loaded env picks it up.

## Publish gap resolved ("typing" but no message)

Symptom: typing indicator + 👀💬 reactions + `turn complete: end_turn`, but no
kind-9 message from the agent. Cause: harness never posts streamed chunks; its
system prompt tells the model to run `buzz messages send` itself — impossible
for a text-only adapter (zero `tool_call`s on the wire prove nothing executed).
Fix = adapter parses channel UUID + reply-to from `[Context]` and publishes the
reply via execFileSync of the buzz CLI (stdin `--content -`). Also strip
fenced bash blocks and the `[CEO Agent]` prefix from model output before
publishing. Full detail in SKILL.md § "The publish gap". Verified: clean
single-sentence threaded replies landing in-channel.

## Cleanup done

- Deleted duplicate seed `#general` (`9f28288a-...`): FK-safe order in one tx —
  migrate members to surviving channel → DELETE thread_metadata →
  channel_members → channels. Harness restarted → "discovered 7 channel(s)".
- Seed identities (Tyler/Alice/Bob/Charlie/seed-agent) KEPT intentionally:
  user plans to convert them into per-department agent identities next phase.

## Test-suite note

ceo-agent `npm run test`: 493/494 core + 55/55 components. The single failure
(`upload directory and file are not group/world readable`) is pre-existing and
POSIX-only: NTFS ignores mkdir modes so the 0o700 assertion can never pass on
Windows. Do not weaken the test or add Windows special-cases upstream.
