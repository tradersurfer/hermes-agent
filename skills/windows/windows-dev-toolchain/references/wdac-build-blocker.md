# WDAC / Device Guard blocking cargo build scripts (Windows)

## Symptom
A Rust `cargo build` / `cargo run` fails with os error 4551 on a *different* crate each time you retry:

```
error: failed to run custom build command for `serde v1.0.228`
Caused by:
  could not execute process `C:\Users\jorda\buzz\target\debug\build\serde-6c4356d2cdaaf769\build-script-build` (never executed)
Caused by:
  An Application Control policy has blocked this file. (os error 4551)
```

Earlier crates compiled; the failure walks through build-script-bearing crates
(`quote` → `serde` → `serde_core` → `proc-macro2` → `thiserror` …).

## Confirm it is WDAC (not a path/location bug)
Run a signed vs unsigned exe from the SAME directory:
- `C:/Users/jorda/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -c "print('ok')"`  → **runs** (Microsoft-signed)
- any cargo `build-script-build.exe` → **blocked** (unsigned)

Then test relocation — all blocked:
- repo `target/`  → blocked
- `C:\ProgramData\cargo-target\buzz\...\build-script-build` → blocked
- `C:\Windows\Temp\cargo-target\buzz\...\build-script-build` → blocked

Conclusion: the policy blocks **unsigned execution everywhere a user can write**,
not a specific path. Relocating `CARGO_TARGET_DIR` does not help (and see the
git-bash `C:/c/` double-prefix mangling trap in SKILL.md §7).

## What was tried and did NOT help
- `rustup target add x86_64-pc-windows-msvc` + `--target x86_64-pc-windows-msvc`
  (removes the separate `winapi-x86_64-pc-windows-gnu` dlltool blocker, but
  build scripts are still unsigned → still blocked).
- VS 2022 Build Tools install (gives `cl.exe`/`link.exe`) — needed for MSVC
  target, but does not relax WDAC.
- `CARGO_TARGET_DIR` in `ProgramData`, `Windows\Temp`, repo dir — all blocked.
- `cargo clean -p` of the failing crate — it's not a stale-artifact issue; the
  next build script just gets blocked instead.

## Real fixes
1. **WSL2 / Linux userspace (recommended).** Compile inside WSL2 where Windows
   Application Control does not apply:
   ```bash
   wsl --list            # see distros
   # if none: wsl --install  (needs reboot)
   wsl -d Ubuntu
   # inside WSL: cd /mnt/c/Users/jorda/buzz  (or clone into the Linux fs)
   # install rustup + cargo-linux, then:  cargo build --workspace
   ```
   Prefer building on the Linux filesystem (`~`), not the mounted `/mnt/c`, for
   speed. The relay can still bind `ws://localhost:3000`; Docker-for-Windows
   containers are reachable from WSL2 via `localhost` if Docker Desktop has
   "WSL2 integration" on.
2. **WDAC policy exception (IT/admin).** Add the cargo target dir (or a code-
   signing cert) to the CI policy. Outside the agent shell.
3. **Elevated context** only if your org relaxes WDAC for admins (often not).

## Related: the Hermes `.exe` launcher block
`hermes.exe` is blocked with "blocked by your organization's Device Guard
policy". Same WDAC family. Workaround there is to run the CLI via the bundled
python module (`venv/Scripts/python.exe hermes_cli/main.py ...`) — but that
trick does NOT apply to cargo build scripts, because build scripts are dynamic
unsigned exes, not a fixed signed interpreter. See the `hermes-windows-ops`
skill for the Hermes-specific case.
