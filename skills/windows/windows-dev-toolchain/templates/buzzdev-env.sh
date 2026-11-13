#!/usr/bin/env bash
# Reusable env helper for building a Rust/Node/Docker repo from git-bash on a
# Windows machine WITHOUT the repo's Hermit bin/* pointer stubs.
# Source before any build command:  source .buzzdev-env.sh
#
# Adjust <user> and the nvm version to match the machine.
export BUZZ_HOME="/c/Users/jorda/buzz"
# TMPDIR must be a Windows-style path (NOT /tmp) or curl/rustup downloads fail (curl 23).
export TMPDIR="C:/Users/jorda/tmp"
# Real tools first (cargo from rustup, node from nvm-windows, pnpm from npm -g)
export PATH="/c/Users/jorda/.cargo/bin:/c/Users/jorda/AppData/Local/nvm/v24.19.0:/c/Users/jorda/AppData/Roaming/npm:${PATH}"
# MinGW binutils for the windows-gnu Rust target (dlltool.exe)
export PATH="/c/Users/jorda/AppData/Local/WinLibs/ucrt64/mingw64/bin:${PATH}"
# Default to the MSVC target so cargo uses the VS linker (avoids the -gnu dlltool
# blocker). NOTE: this still hits WDAC on build scripts — see wdac-build-blocker.md.
export CARGO_BUILD_TARGET="x86_64-pc-windows-msvc"
# IMPORTANT: if you must set CARGO_TARGET_DIR, use NATIVE Windows form with
# backslashes, never the /c/... git-bash form (it gets mangled to C:/c/...):
#   export CARGO_TARGET_DIR="C:\\ProgramData\\cargo-target\\buzz"
echo "buzzdev: cargo=$(command -v cargo) node=$(command -v node) pnpm=$(command -v pnpm) target=${CARGO_BUILD_TARGET}"
