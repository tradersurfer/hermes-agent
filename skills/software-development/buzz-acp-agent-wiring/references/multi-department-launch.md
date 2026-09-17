# Multi-department agent launcher (Buzz + ceo-agent via ACP)

Verified template for running 6 department agents as separate Buzz identities,
each pinned to its department head via `CEO_DEPARTMENT`. Key properties that
made it work on this host:

- **`BUZZ_RELAY_URL=ws://127.0.0.1:3000`** (IPv4, NOT localhost). WSL2 maps
  `localhost`→`::1`; the relay listens on IPv4. The harness's HTTP `/query`
  side-channel fails on `::1`, blocking all replies.
- **Inline env only** (no `export`, no `source`, no `${!}` indirection) — a
  WSL bash here had broken assignment (`A=1; echo $A` → empty); inline `VAR=val
  command` is reliable.
- **`setsid bash -c '...' &`** so each harness survives the launcher script
  exiting.
- **12s stagger** between launches so 6 cold Node runtimes don't contend for CPU
  (avoids the 60s ACP `initialize` timeout).
- One harness per agent pubkey — never share a key across two buzz-acp instances
  (causes EPIPE crashes and circuit-breaker loops).

For one-command startup (Docker + relay + agents), use `buzz.bat` at the repo
root on Windows (wake-up word "buzz"). It ensures Docker Desktop is running
(starts it if needed), then calls `bash /home/jordan/buzzup.sh` in WSL2.
`buzzup.sh` truncates each log (`: > $LOG/acp_${name}.log`), checks relay
readiness, then launches all 7 agents with 12s stagger. See
`references/verified-recipes.md` §11 for the relay health-check race pitfall.

```bash
#!/usr/bin/env bash
set -u
NODE_BIN=/home/jordan/node24/bin/node
ACPBIN=/home/jordan/buzz-target/debug/buzz-acp
RELAY=ws://127.0.0.1:3000
AGENT_JS=/mnt/c/Projects/ceo-agent-public/acp/acp-agent.js
LOGDIR=/home/jordan/buzzlogs
mkdir -p "$LOGDIR"

# name|nsec|pubkey|department-id (verify each via getPublicKey before trusting)
agents=(
  "CEO Agent|290126cd58133b934671f5182b60e3bf4f3cdbf6c0b47ec54cce0e97d005de61|a45fedb27671ebb3d1c80deb999023e31f58dc7127c480fef3f9d2a847d4fdd9|__ceo__"
  "CFO Agent|77f5ce6253ac8b84fce957f01ae1acb1296093234078b35d892282263a78b385|832a6d2bfafd2e8bfc5edc881464ecf2e8805eb0b82156e3e9b1287bd8fbb691|finance"
  "COO Agent|6166d682325bc140487b70bc904046a90e6e2a50187ce6c3285d53e26932b57b|649f73cc9852faab9cc3a0ddd8d531e149ce88a38e7ce536e23402a5b1128ade|operations"
  "CTO Agent|11687bafd1e16c944910ffd5fc8b229046884402397d7c2f9a56c536e877cc16|43c58c549e0f1ae4c6995ee9140f083d7225f3a913dd1aaf75e0127e1e17d775|technology"
  "CMO Agent|764f69bf67f44ec9eb8385c78333d132ddcd1e6b4e9af421c89eafa57d5a7790|ad30e03d8d902dce7455bf97a72989d70b66264a926916185dc78aa248fc84d4|marketing"
  "CHRO Agent|5bebb162026ffb3895071eb885d30134d7a6569913fdb917ae756bbb322b08e8|af1d02be1a40333893cd54011efe648a3cc19df6f6e1cf0c7930fa9f7ec53a2b|people"
  "CLO Agent|53166056580b2f20b7d3923f98a8c9ec402e1ff076389c94460c81fb56ac02ef|c3b9f7b657b29a8a52dbbbc801b64e33fb10f1f486c4182edf4fb6a5c35190f4|legal"
)

for entry in "${agents[@]}"; do
  IFS='|' read -r name nsec pub dept <<< "$entry"
  echo "launching $name (dept=$dept)..."

  # Profile (inline env, fire-and-forget)
  PATH=/home/jordan/node24/bin:/home/jordan/buzz-target/debug:/home/jordan/.cargo/bin:/usr/local/bin:/usr/bin:/bin \
  CARGO_TARGET_DIR=/home/jordan/buzz-target \
  BUZZ_PRIVATE_KEY="$nsec" BUZZ_RELAY_URL="$RELAY" \
  /home/jordan/buzz-target/debug/buzz users set-profile --name "$name" --about "$dept department head agent" >/dev/null 2>&1 &

  # Pinned harness — setsid so it survives the parent shell exiting
  DEPT_ARG=""
  if [ "$dept" != "__ceo__" ]; then DEPT_ARG="CEO_DEPARTMENT=$dept "; fi

  setsid bash -c "PATH=/home/jordan/node24/bin:/home/jordan/buzz-target/debug:/home/jordan/.cargo/bin:/usr/local/bin:/usr/bin:/bin CARGO_TARGET_DIR=/home/jordan/buzz-target HOME=/home/jordan BUZZ_PRIVATE_KEY=$nsec BUZZ_RELAY_URL=$RELAY ${DEPT_ARG}RUST_LOG=info,buzz_acp=info /home/jordan/buzz-target/debug/buzz-acp --relay-url $RELAY --agent-command $NODE_BIN --agent-args $AGENT_JS --subscribe all --respond-to anyone >> $LOGDIR/acp_${dept}.log 2>&1" &

  sleep 12  # stagger cold Node runtimes
done
echo "=== all 7 harnesses launched; health-checking in 45s ==="
sleep 45

for entry in "${agents[@]}"; do
  IFS='|' read -r name nsec pub dept <<< "$entry"
  log="$LOGDIR/acp_${dept}.log"
  ch=$(grep -oE "discovered [0-9]+ channel" "$log" 2>/dev/null | tail -1)
  on=$(grep -c "presence set to online" "$log" 2>/dev/null)
  echo "$name: online=$on | ${ch:-NO_CHANNELS}"
done
echo "=== done. ==="
```

## Verify

After launch, for each dept log:
```
grep -c "presence set to online" $LOGDIR/acp_<dept>.log   # expect >=1
grep "discovered" $LOGDIR/acp_<dept>.log                  # expect "discovered N channel(s)" N>0
```
If `discovered 0 channel(s)` → check `SELECT host FROM communities;` matches
the URL you used, then relaunch that harness (discovery runs once at boot).
