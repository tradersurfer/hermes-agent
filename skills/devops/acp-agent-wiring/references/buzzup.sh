#!/usr/bin/env bash
# ===========================================================================
# buzzup.sh — One-command Buzz startup: relay + 7 department agents.
#
# Usage:  bash /home/jordan/buzzup.sh
#
# Key fixes:
#   * ws://127.0.0.1:3000 (IPv4) — WSL2 maps localhost→::1, breaking /query
#   * Correct nsec→pubkey mappings (verified against DB channel_members)
#   * 10s stagger between agent launches (avoids HTTP 429 cascade)
#   * Per-agent log truncation (avoids stale log confusion)
#   * setsid + nohup for durable daemonization
#
# Department agent identities (pubkey):
#   CEO     a45fedb2...  nsec: 290126cd... (no dept pin)
#   CFO     832a6d2b...  nsec: 77f5ce62...  dept: finance
#   COO     649f73cc...  nsec: 6166d682...  dept: operations
#   CTO     43c58c54...  nsec: 11687baf...  dept: technology
#   CMO     ad30e03d...  nsec: 764f69bf...  dept: marketing
#   CHRO    af1d02be...  nsec: 5bebb162...  dept: people
#   CLO     c3b9f7b6...  nsec: 53166056...  dept: legal
# ===========================================================================
set -u
mkdir -p /home/jordan/buzzlogs

export PATH="/home/jordan/node24/bin:/home/jordan/buzz-target/debug:/home/jordan/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
export HOME=/home/jordan
RELAY="ws://127.0.0.1:3000"
NODE="/home/jordan/node24/bin/node"
ACP="/home/jordan/buzz-target/debug/buzz-acp"
RLY="/home/jordan/buzz-target/debug/buzz-relay"
AGENT="/mnt/c/Projects/ceo-agent-public/acp/acp-agent.js"
LOG="/home/jordan/buzzlogs"

# --- Check Docker ---
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker not running. Start Docker Desktop, then re-run."
  exit 1
fi
docker start buzz-postgres buzz-redis buzz-minio >/dev/null 2>&1 || true
sleep 2
echo "Docker: OK | Containers: started"

# --- Relay ---
if curl -sf --max-time 2 "$RELAY/_readiness" 2>/dev/null | grep -q ready; then
  echo "Relay: already running"
else
  echo "Starting relay..."
  cd /mnt/c/Users/jorda/buzz
  RUST_LOG=warn BUZZ_RECONCILE_CHANNELS=true \
  nohup setsid "$RLY" > "$LOG/relay.log" 2>&1 &
  for i in $(seq 1 30); do
    curl -sf --max-time 2 "$RELAY/_readiness" 2>/dev/null | grep -q ready && break
    sleep 1
  done
fi
echo "Relay: $(curl -sf --max-time 2 "$RELAY/_readiness" 2>/dev/null)"
sleep 5

# --- Launch function ---
# Creates a per-agent launcher script to avoid bash var expansion bugs in setsid
launch() {
  local name="$1" nsec="$2" dept="$3"
  local launcher="/tmp/run_${name}.sh"
  {
    echo "#!/usr/bin/env bash"
    echo "export PATH=$PATH"
    echo "export HOME=/home/jordan"
    echo "export BUZZ_PRIVATE_KEY=$nsec"
    echo "export BUZZ_RELAY_URL=$RELAY"
    echo "export RUST_LOG=info,buzz_acp=info"
    [ -n "$dept" ] && echo "export CEO_DEPARTMENT=$dept"
    echo "exec $ACP --relay-url $RELAY --agent-command $NODE --agent-args $AGENT --subscribe all --respond-to anyone"
  } > "$launcher"
  chmod +x "$launcher"
  : > "$LOG/acp_${name}.log"   # truncate to avoid stale log confusion
  setsid bash "$launcher" </dev/null >"$LOG/acp_${name}.log" 2>&1 &
  disown
  sleep 10
}

echo "Launching agents..."
launch ceo 290126cd58133b934671f5182b60e3bf4f3cdbf6c0b47ec54cce0e97d005de61 ""
launch finance 77f5ce6253ac8b84fce957f01ae1acb1296093234078b35d892282263a78b385 finance
launch operations 6166d682325bc140487b70bc904046a90e6e2a50187ce6c3285d53e26932b57b operations
launch technology 11687bafd1e16c944910ffd5fc8b229046884402397d7c2f9a56c536e877cc16 technology
launch marketing 764f69bf67f44ec9eb8385c78333d132ddcd1e6b4e9af421c89eafa57d5a7790 marketing
launch people 5bebb162026ffb3895071eb885d30134d7a6569913fdb917ae756bbb322b08e8 people
launch legal 53166056580b2f20b7d3923f98a8c9ec402e1ff076389c94460c81fb56ac02ef legal

echo "=== All 7 agents launched ==="
echo "Check discovery: grep 'discovered' /home/jordan/buzzlogs/acp_legal.log"
echo "Watch relay: tail -f /home/jordan/buzzlogs/relay.log"
