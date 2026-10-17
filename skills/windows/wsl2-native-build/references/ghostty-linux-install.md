# Ghostty install on WSL2 (Ubuntu) — community AppImage

## Why this matters
Ghostty has **no official Linux binaries**. The project only distributes prebuilt macOS binaries. Linux users must rely on distro packages or community builds. This note covers the path that works on WSL2 Ubuntu 24.04.

## Verified install (2026-09-04, WSL2 Ubuntu 24.04.1 LTS, x86_64)

### Option A: AppImage (pkgforge-dev community build) — WORKED
The community-maintained AppImage from `pkgforge-dev/ghostty-appimage` works out of the box on WSL2:

```bash
# Download (from inside WSL2)
curl -sL -o /tmp/Ghostty-1.3.1-x86_64.AppImage \
  https://github.com/pkgforge-dev/ghostty-appimage/releases/download/v1.3.1/Ghostty-1.3.1-x86_64.AppImage
chmod +x /tmp/Ghostty-1.3.1-x86_64.AppImage

# Verify it runs
/tmp/Ghostty-1.3.1-x86_64.AppImage --version
# -> Ghostty 1.3.1

# Install to user bin (no sudo needed if using ~/.local/bin)
mkdir -p ~/.local/bin
cp /tmp/Ghostty-1.3.1-x86_64.AppImage ~/.local/bin/ghostty
```

**Note**: `~/.local/bin` may already be on PATH (Ubuntu often sources it via `.bashrc`). Verify with `echo $PATH`. If not, add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc`.

### Option B: Snap (also available in Ubuntu repos)
Snap is available but **sandboxing can be problematic under WSL2** (Wayland display, filesystem access). The AppImage is more reliable.

```bash
sudo snap install ghostty --classic
```

### Option C: Build from source
If you need the very latest (tip) or a specific distro package is unavailable, build from source using the WSL2 technique described in the `wsl2-native-build` skill. Ghostty uses Zig, so the Rust toolchain approach in `wsl2-native-build` applies — but Ghostty's build system is Zig-based, not Cargo.

## Pitfalls
- **No official Linux binary exists** — the "Binaries and Packages" page explicitly states Ghostty only officially distributes for macOS. All Linux options are community or distro-maintained.
- **AppImage needs a display server** — Ghostty (GTK) needs a Wayland/X11 compositor. Under WSL2 with GPU access, this works if the host has a display server. Pure headless WSL2 without GPU won't render the GUI.
- **`sudo` in background WSL2 calls hangs** — avoid `sudo` in background (`&`) subshells or after prior `sudo` commands that may have left a lock. Use `install` or `cp` without sudo, or run `sudo` in a fresh foreground call.
- **Snap vs AppImage**: Snap is available in Ubuntu repos but the sandbox can block Wayland/X11 forwarding in WSL2. The AppImage from pkgforge is the more reliable path.
- **Package managers**: If your distro has Ghostty in its default repos (Arch, Ubuntu 26.04+, NixOS, etc.), that's the cleanest option. For Ubuntu < 26.04, neither apt nor snap provide Ghostty.

## Download URL template (for future versions)
```
https://github.com/pkgforge-dev/ghostty-appimage/releases/download/v{VERSION}/Ghostty-{VERSION}-x86_64.AppImage
```
