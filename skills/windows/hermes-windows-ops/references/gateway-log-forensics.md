# Gateway / Telegram Log Forensics

Logs live in `~/.hermes/logs/` (i.e. `C:\Users\jorda\AppData\Local\hermes\logs\`).
Several files exist; know which is authoritative.

## Log files
- `gateway.log` — main gateway stdout/stderr. Reliable for "Channel directory built" and "set_my_commands OK".
- `gateway-stdio.log` — captured stdio stream. Can **lag** the task-launched process; don't rely on its tail alone.
- `gateway-exit-diag.log` — **most authoritative for lifecycle**. One JSON object per event:
  - `{"tag":"gateway.start","pid":...,"argv":[...]}` — process booted.
  - `{"tag":"gateway.previous_unclean_exit",...}` — prior crashed (SIGKILL/OOM).
  - `{"tag":"asyncio.run.SystemExit","code":78,...}` — non-retryable exit (e.g. bad Telegram token).
  - `{"tag":"gateway.exit_clean"}` — clean stop.
- `gateway.pid` / `gateway.lock` — current PID + kind (`hermes-gateway`), argv, start_time, hermes_home. `gateway status` reads these.

## Telegram connect patterns (in gateway.log)
SUCCESS:
```
[Telegram] Connecting to Telegram (attempt 1/8)…
[Telegram] set_my_commands OK for scope BotCommandScopeDefault (60 cmds)
[Telegram] Telegram menu: 60 commands registered, 2 hidden (over 60 limit)
Channel directory built: 1 target(s)
```
FAILURE (rejected/revoked token — gateway exits cleanly, non-retryable):
```
[Telegram] Connecting to Telegram (attempt 1/8)…
[Telegram] Failed to connect to Telegram: The token `123456:ABC…` was rejected by the server.
✗ telegram failed to connect
Gateway exiting cleanly: telegram: Telegram bot token rejected: …
```
Fix: regenerate token via @BotFather, update `TELEGRAM_BOT_TOKEN` in `.env`, `gateway restart`. The gateway will NOT retry a rejected token — it exits.

## Proving the gateway is alive
Prefer `gateway status` ("✓ Gateway process running (PID: N)") over log tails.
A task-launched gateway may sit at 5–22 MB RAM briefly and still be healthy.
A truly hung/stopped one shows NO new "Starting Hermes Gateway" entry in
`gateway-exit-diag.log` and no new "Channel directory built" line in `gateway.log`.

## Handover verification checklist
1. `gateway stop` → "✓ Gateway stopped".
2. `schtasks /run /tn Hermes_Gateway` → "SUCCESS: Attempted to run…".
3. Wait ~10s.
4. `gateway status` shows a NEW PID (different from the manual one).
5. `gateway.log` shows a fresh "Channel directory built: 1 target(s)" and
   "set_my_commands OK" after the stop's "Disconnected from Telegram".
   (If you only see the old banner, the task process may still be booting — wait longer.)
