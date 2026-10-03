# Windows git-bash toolchain — error transcripts & fixes

Exact errors seen driving a Windows 10 dev box (user `jorda`) from git-bash, and the commands that resolved them. Forward slashes in `C:/Users/...` paths work in git-bash.

## 1. curl write error 23 (any download to /tmp)
```
curl: (23) client returned ERROR on write of 15741 bytes
```
Cause: git-bash `/tmp` is an MSYS path some downloaders reject. Fix: write to a Windows path.
```bash
curl -sSL --max-time 30 -o "C:/Users/jorda/tmp/rustup.sh" https://sh.rustup.rs   # OK 29250 bytes
# BAD:  curl -o /tmp/rustup.sh ...   -> 23
```

## 2. rustup install fails (downloads rustup-init.exe to /tmp)
```
info: downloading installer
warn: curl: (23) client returned ERROR on write of 16384 bytes
error: command failed: downloader .../rustup-init.exe /tmp/tmp.FRMB0qn2fH/rustup-init.exe
```
Fix: point TMPDIR at a Windows path before running the installer.
```bash
export TMPDIR="C:/Users/jorda/tmp"; unset TEMP TMP
sh rustup.sh -y --default-toolchain 1.95.0 --profile default
# -> rustc 1.95.0 / cargo 1.95.0 installed (x86_64-pc-windows-gnu)
```

## 3. cargo build: dlltool missing (windows-gnu target)
```
error: error calling dlltool 'dlltool.exe': program not found
error: could not compile `getrandom` (lib) due to 1 previous error
```
Fix: provide MinGW binutils. Prefer the portable zip over the winget installer (winget WinLibs often stalls on a silent UAC prompt).
```bash
curl -sSL -o winlibs.zip "https://github.com/brechtsanders/winlibs_mingw/releases/download/16.1.0posix-14.0.0-ucrt-r4/winlibs-x86_64-posix-seh-gcc-16.1.0-mingw-w64ucrt-14.0.0-r4.zip"
mkdir -p "C:/Users/jorda/AppData/Local/WinLibs/ucrt64"
cd "C:/Users/jorda/AppData/Local/WinLibs/ucrt64" && unzip -q winlibs.zip
# PATH must include the NESTED dir:
export PATH="/c/Users/jorda/AppData/Local/WinLibs/ucrt64/mingw64/bin:$PATH"
dlltool --version   # Binutils 2.47
gcc --version      # MinGW-W64 x86_64-ucrt
```

## 4. nvm-windows: node not on PATH after `nvm use`
```
nvm use 24   -> Now using node v24.19.0
node --version  -> bash: node: command not found
```
Fix: add the versioned dir explicitly (nvm modifies Windows PATH, not the bash shell's).
```bash
export PATH="/c/Users/jorda/AppData/Local/nvm/v24.19.0:$PATH"
node --version   # v24.19.0
```
Install pnpm with npm (corepack is broken under nvm-windows): `npm install -g pnpm@11.4.0`.

## 5. python3 is a Microsoft Store stub
```
python3 --version  -> Python was not found; run without arguments to install from the Microsoft Store
```
Fix: `winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent`
Use `C:/Users/jorda/AppData/Local/Programs/Python/Python312/python.exe` on PATH.

## 6. Hermit bin/* stubs are inert
Files like `bin/just`, `bin/cargo`, `bin/node` contain a single line (e.g. `.just-1.46.0.pkg`) — package pointers, not executables. `bin/activate-hermit` bootstrap errors under git-bash strict mode (`HERMIT_STATE_DIR_RAW: unbound variable`). Resolution: install the REAL tools (rustup/cargo, nvm/node, winget pnpm, system `just`) and replicate `scripts/dev-setup.sh` by hand (docker compose up; `cargo run -p <admin> -- migrate`; `pnpm install`).

## 7. Docker Desktop: daemon down until reboot
`winget install Docker.DockerDesktop` -> "Successfully installed", but `docker info` fails until a **reboot** (WSL2 backend). `docker --version` works regardless. Approve the UAC prompt if the installer stalls.

## 8. Decisive build-error debugging pattern (unfinished in session)
A `cargo build` died with:
```
error[E0463]: can't find crate for `yoke_derive`
  --> yoke-0.8.2/src/lib.rs:60:9  (pub use yoke_derive::Yokeable;)
error[E0432]: unresolved imports `crate::Yokeable`
error: could not compile `yoke` (lib)
```
Key facts established: `yoke 0.8.2` depends on `yoke-derive 0.8.2` (hyphen) in `Cargo.lock`; `yoke-derive` is `proc-macro = true` and **builds fine standalone** (`cargo build -p yoke-derive` -> exit 0). The `yoke_derive` (underscore) reference in code is normal hyphen→underscore normalization, NOT the bug. The "can't find crate" means the proc-macro dep wasn't actually linked into `yoke`'s build.

Not yet resolved in-session. Next steps to try (in order):
1. `cargo clean -p yoke -p yoke-derive` then `cargo build -p yoke` (clear stale incremental artifacts from the earlier dlltool-failed build).
2. `cargo tree -i yoke-derive -e features` to see which crate enables `yoke/derive` and whether the feature is actually propagated in the unified feature set.
3. `cargo update -p yoke --precise <newer>` if 0.8.2 has a known proc-macro resolution bug; otherwise bump the dependent crate that pulls `yoke/derive`.

Lesson: when cargo reports a downstream crate's error (e.g. `yoke` can't find `yoke_derive`), build the named dependency in isolation to surface the true cause.
