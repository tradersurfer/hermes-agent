> **SUPERSEDED — see `references/ceo-agent-adapter.md`** for the current state (live loop confirmed, publish fix, cleanup done). Kept only as historical snapshot; do not follow its "Outstanding" list.

# ceo-agent ACP adapter — working example

Adapter file: `C:\Projects\ceo-agent-public\acp\acp-agent.js` (Node, no deps).
Verified live: initialize → session/new → session/prompt with a real model reply.

## Key design decisions
- **Reuse the server seam, not the CLI.** `bin/chat.js` is readline-interactive; instead require `lib/ceoAgentServer.js` which exports `getRuntime` (cached runtime), `ensureModelsResolved`, `buildSystemPrompt`, and pre-built provider clients (`openRouterClient`, etc.) — identical to what the web `/api/chat` route uses.
- **`process.chdir(repo root)` at startup** — `lib/ceoAgentServer.js` resolves `ROOT = path.resolve(process.cwd())`, so cwd must be the ceo-agent repo when the harness spawns the adapter from elsewhere.
- **One shared runtime across all sessions** (matches web server behavior); sessionId generated locally, sessions map kept only for protocol compliance.
- **Skill dispatch first** (`ceo-core/skillDispatch` — `/skill` or `@skill {json}` syntax), then @department routing via `runtime.routeTask`, then provider call. Mirrors route.ts exactly.
- Reply prefix `[<agentName>]` when routed away from CEO so channel readers see which department answered.

## Launch (WSL2, on WDAC host)
```bash
export BUZZ_PRIVATE_KEY=<agent key hex>       # minted via buzz-admin generate-key
export BUZZ_RELAY_URL=ws://localhost:3000
buzz-acp --relay-url $BUZZ_RELAY_URL \
  --private-key $BUZZ_PRIVATE_KEY \
  --agent-command "$HOME/node24/bin/node" \
  --agent-args /mnt/c/Projects/ceo-agent-public/acp/acp-agent.js \
  --subscribe mentions --respond-to anyone
```
Launcher script kept at `C:\Users\jorda\buzz\.wsl_ceo_agent_run.sh`.

## Test handshake without Buzz
```bash
cd /c/Projects/ceo-agent-public
printf '%s\n%s\n%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"session/new","params":{}}' \
 '{"jsonrpc":"2.0","id":3,"method":"session/prompt","params":{"sessionId":"s1","prompt":[{"type":"text","text":"hello"}]}}' \
 | node acp/acp-agent.js
```

## Outstanding at time of writing
- Live @mention loop through buzz-acp not yet confirmed (harness running; awaiting desktop mention). If mention subscription doesn't fire, switch `--subscribe all`.
- Per-department subagents as separate Buzz identities: deferred until single-CEO agent confirmed working; each needs own keypair + membership + harness instance.
- MCP exposure for Hermes users: separate later project (repo has ADR-011 outbound MCP).
