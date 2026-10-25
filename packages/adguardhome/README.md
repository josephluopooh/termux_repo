# AdGuard Home

AdGuard Home 0.107.79, built from the [official source release](https://github.com/AdguardTeam/AdGuardHome/releases/tag/v0.107.79)
for aarch64 Android/Bionic. The matching stable dashboard is compiled from the
same source using its integrity-pinned npm lockfile. This is an experimental
Termux port; it does not use proot or ship an upstream Linux/glibc executable.

```sh
pacman -Syu termux_repo-aarch64/adguardhome
adguardhome
```

Open `http://127.0.0.1:3000`. The launcher runs in the foreground and copies its
initial configuration into `${XDG_DATA_HOME:-$HOME/.local/share}/adguardhome/`.
Set `ADGUARDHOME_WORK_DIR` to an absolute directory to use separate state.
Stop with Ctrl-C and run the same command to reopen the saved configuration,
query log and statistics. Updates use Pacman; in-app updates are disabled.

The dashboard and DNS listeners default to **localhost only**, on HTTP port 3000
and UDP/TCP DNS port 5353. There is no initial password. Other local apps may be
able to reach localhost, so configure authentication before storing sensitive
query history or changing the bind address. No credentials are created by the
package or tests. Do not expose the unauthenticated dashboard to a network.

Choose an upstream resolver in **Settings → DNS settings** before using DNS.
The initial upstream `127.0.0.1:9` is deliberately inactive, so installation does
not silently select an external DNS provider. Add filter lists or custom rules
in the dashboard. Automatic external filter downloads, reverse lookups, host
file monitoring and DHCP are disabled in the initial configuration.

This package does **not** automatically filter the whole phone. Applications
must explicitly query `127.0.0.1:5353`; Android's ordinary DNS settings generally
cannot select this nonstandard port. A system-wide VPN/DNS integration, port 53,
DHCP, routing, privileged network operations and OS service installation are
outside this rootless package's tested scope. No Android network settings are
changed. The packaged executable is in `$PREFIX/libexec/adguardhome/AdGuardHome`;
use the `adguardhome` launcher for the safe paths and defaults.

## Validation

The release gate installs the real Pacman package in a native aarch64
Termux-Pacman container and runs [smoke-test.py](smoke-test.py). It checks the
bundled dashboard HTML/JavaScript, status and configuration APIs, rootless UDP
and TCP DNS, forwarding to a synthetic localhost resolver, blocked responses,
and custom DNS rewrites. It restarts the server and checks saved rules, rewrites,
query log and statistics. All test domains use `.test`, all network listeners
use loopback, and temporary state is removed. No external upstream, account,
credentials or host resolver changes are used.

A Linux host build is only a harness preflight. Physical Android hardware,
SELinux restrictions, background process termination, sleep/wake and Wi-Fi/mobile
transitions still need device testing; container results do not establish those.

## Sources and licenses

AdGuard Home is GPL-3.0; its full license and Go/npm dependency notices are
installed under `$PREFIX/share/doc/adguardhome/`. The release includes
`adguardhome-0.107.79-<package-revision>-source.tar.gz` with the source, packaging recipe, matching
frontend dependencies and runtime Go module source. Supplemental npm notices
missing from distribution tarballs are copied from pinned upstream commits;
[their manifest](client-license-supplements/manifest.json) records URLs/hashes.
Some upstream npm packages publish their grant only in README or package
metadata; those original files are retained as well. Standard Termux runtime
libraries come from the official repository; the only explicit dependency is
`ca-certificates`. No TUR recipe was used.
