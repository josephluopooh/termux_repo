# Uptime Kuma (experimental)

[Uptime Kuma 2.5.7](https://github.com/louislam/uptime-kuma/releases/tag/2.5.7)
is built from upstream source, including its matching monitoring dashboard.
This Android port is experimental. It uses official Termux `nodejs-lts`,
`libsqlite`, `libc++`, and CA certificates, with private npm dependencies owned
by Pacman. No npm install runs on your device.

```sh
pacman -Syu termux_repo-aarch64/uptime-kuma
uptime-kuma
```

Open `http://127.0.0.1:3001` on the device. On first launch choose SQLite and
create your own account. No default account or password is installed. Stop with
Ctrl-C. Start again with `uptime-kuma` to resume the saved monitors.

Data lives in `${XDG_DATA_HOME:-$HOME/.local/share}/uptime-kuma`, separate from
the Pacman-owned application. `DATA_DIR`, `UPTIME_KUMA_HOST`, and
`UPTIME_KUMA_PORT` override those defaults. The launcher defaults to localhost;
choosing a non-loopback host exposes the setup/dashboard service. Use suitable
authentication and HTTPS before making it reachable elsewhere. The launcher
uses a private umask. Updating/removing the package does not erase user data.

Pacman manages application updates. Upstream update hints are off unless
`UPTIME_KUMA_CHECK_UPDATE=1` is set; no application self-update is enabled.

## Native dependencies and licenses

The upstream `package-lock.json` fixes npm versions and tarball integrity hashes.
The build disables npm lifecycle scripts, builds the dashboard, prunes build
dependencies, and removes all bundled platform binaries. It compiles the four
upstream `@louislam/sqlite3` C++ sources against official Termux Node headers and
shared SQLite using the Android toolchain. The sole shipped Node addon is
`napi-v6-android-arm64/node_sqlite3.node`; it uses stable N-API 6. No glibc or
proot runtime is involved.

Uptime Kuma is MIT licensed. Published dependency license/notice files,
README attribution, metadata, and locked integrity hashes are preserved under
`$PREFIX/share/doc/uptime-kuma/dependency-licenses`; this includes frontend build
dependencies. Some npm tarballs provide a license declaration or README rather
than a standalone license file; the manifest records that distinction. Runtime
module distributions retain their upstream attribution files.
Hash-verified supplementary texts from official project commits are included
where npm omitted them, along with the exact secp256k1 notice for the WASM
dependency. `_supplemental/manifest.json` records their provenance, distinguishing
npm source revisions from project snapshots. Distributions whose historical
source only declares a license are listed in `declarations-only.json`; standard
license terms are supplied separately without inventing copyright owners.

## Validation and limits

The release gate installs the real aarch64 package in a disposable native
Termux-Pacman container and checks the dashboard HTML and built JavaScript,
SQLite addon loading, synthetic account setup/login, a loopback HTTP monitor
through UP, DOWN, and recovery, SQLite persistence, clean shutdown, and a second
process restoring the account and resuming the monitor. Synthetic accounts and
temporary data are deleted. No external account, webhook, or real credentials
are used.

Those checks do not establish physical Android reliability. Android background
process limits, Doze, battery restrictions, OEM behavior, browser rendering,
and long-running monitor delivery need device testing. Optional integrations
such as notifications, external databases, browser monitors, ICMP/ping,
Docker, Cloudflare tunnels, and discovery are untested here. No browser,
Docker daemon, cloudflared, or Oracle thick-mode client is bundled. SSH uses
its JavaScript crypto fallback; Oracle's JavaScript thin mode is retained.
The package does not automatically start at boot or change device networking.
