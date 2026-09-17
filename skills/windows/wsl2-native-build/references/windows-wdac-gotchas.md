# Windows WDAC / WSL2 build gotchas — command recipes

## 1. CRLF in Windows-authored shell/.env files
WSL bash rejects CRLF endings: `set: pipefail\r: invalid option name`.
```bash
# inside WSL2
sed -i "s/\r$//" scripts/seed-local-community.sh
sed -i "s/\r$//" .env
file scripts/seed-local-community.sh   # expect "ASCII text executable", not "with CRLF"
```

## 2. git-bash expands $HOME before WSL sees it
`wsl.exe -d Ubuntu -- bash -c 'export PATH=$HOME/node24/bin...'` turns `$HOME` into `C:/Users/jorda`.
Fix: write a static script on Windows, copy it in, run it.
```bash
# write C:/Users/jorda/buzz/.wsl_build.sh (literal $HOME, no expansion at write time)
wsl.exe -d Ubuntu -- bash -c 'export PATH=/usr/local/bin:/usr/bin:/bin; cp /mnt/c/Users/jorda/buzz/.wsl_build.sh /tmp/build.sh; bash /tmp/build.sh'
```
Inside the script, set a clean PATH first line: `export PATH="$HOME/node24/bin:$HOME/.cargo/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"`.

## 3. Slow WSL2 network egress
Downloading Node/Rust tarballs inside WSL2 times out (got 3MB/31MB in 300s).
Fix: download on the Windows side (fast), copy into WSL.
```powershell
# Windows git-bash
curl -sSL --max-time 240 -C - -o node24-linux.tar.xz https://nodejs.org/dist/v24.19.0/node-v24.19.0-linux-x64.tar.xz
```
```bash
# WSL2
cp /mnt/c/Users/jorda/tmp/node24-linux.tar.xz /tmp/node24.tar.xz
xz -t /tmp/node24.tar.xz && echo XZ_VALID
tar -xJf /tmp/node24.tar.xz -C ~/node24 --strip-components=1
```

## 4. python3 → Microsoft Store stub (Windows)
`python3` on Windows git-bash opens the Store. Create a shim:
```bash
mkdir -p /c/Users/jorda/tmp/shim
printf '#!/bin/sh\nexec "/c/Users/jorda/AppData/Local/Programs/Python/Python312/python.exe" "$@"\n' > /c/Users/jorda/tmp/shim/python3
chmod +x /c/Users/jorda/tmp/shim/python3
export PATH="/c/Users/jorda/tmp/shim:$PATH"   # put first
python3 --version   # -> Python 3.12.10
```

## 5. CARGO_TARGET_DIR path mangling
git-bash `/c/ProgramData/cargo-target/buzz` becomes `C:/c/ProgramData/cargo-target/buzz` (double prefix) → build-script exe blocked at wrong path.
Fix A: use Windows-native form `export CARGO_TARGET_DIR="C:\ProgramData\cargo-target\buzz"`.
Fix B (preferred): build entirely inside WSL2 with `export CARGO_TARGET_DIR=$HOME/buzz-target` (Linux path, no mangling, WDAC N/A).

## 6. WSL2 unresponsive under heavy build (`0x8007274c`)
`A connection attempt failed ... Wsl/Service/0x8007274c` is a transient VM hiccup under build load, not a build failure. The background build process keeps running. Retry the check after a moment; do not restart the build.

## 7. Hermit `bin/*` pointer stubs
Buzz (and similar repos) ship inert Hermit pointer files: `bin/cargo`, `bin/just`, `bin/node` are markers, not executables. `dev-setup.sh` calls `${REPO}/bin/just` / `${REPO}/bin/cargo` — these need Hermit. Without Hermit, call your real `cargo`/`just`/`pnpm` directly. WinLibs MinGW provides `dlltool.exe` if a windows-gnu Rust target needs it.

## 8. Docker bridge Windows <-> WSL2
- From WSL2: reach Windows-side containers at `localhost:<port>` (Postgres 5432, Redis 6379, MinIO 9000, Keycloak 8180).
- `docker` CLI is NOT in WSL2 by default → run `docker compose`/`docker exec` from Windows git-bash.
- Seed scripts that call `docker exec buzz-postgres psql` work from Windows; those needing `python3` need the shim from #4.
