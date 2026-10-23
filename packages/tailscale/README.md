# Tailscale

Native aarch64 Android/Bionic build of upstream Tailscale **1.104.2**. The
package includes `tailscale` and `tailscaled`; it does not use proot. It reuses
official Termux CA certificates and preserves upstream's standalone Android
interface fallback and DNS support.

```sh
pacman -Syu termux_repo-aarch64/tailscale
tailscaled --socks5-server=127.0.0.1:1055 \
  --outbound-http-proxy-listen=127.0.0.1:1056
```

Keep the daemon running, then use another Termux session for `tailscale status`.
Joining a tailnet is an explicit user action: `tailscale up --accept-dns=false`.
Follow its login URL using your own account; installing or starting this package
does not authenticate. Applications must explicitly use the SOCKS5 or HTTP
proxy (for example `ALL_PROXY=socks5h://127.0.0.1:1055`). Keep proxy listeners
bound to loopback.

The launcher defaults to **non-root userspace networking**, private persistent
state under `${XDG_STATE_HOME:-$HOME/.local/state}/tailscale`, and a local Unix
socket at `$TMPDIR/tailscaled.sock`. It disables upstream log uploads with
`--no-logs-no-support`. State includes credentials after you log in; protect it.
No service is automatically enabled, and Android may stop Termux in the
background. The upstream daemon is also available at `$PREFIX/libexec/tailscaled`;
explicit command-line flags override the launcher's defaults.

Userspace mode does **not** provide a full-device Android VPN, automatically
route other apps, or install Android's VPN service. Use the official
[Tailscale Android app](https://tailscale.com/download/android) for full-device
VPN integration. Kernel TUN, root routing, exit-node/subnet routing and
integration with another VPN are outside this package's tested scope. The
Tailscale SSH server is omitted: its upstream implementation excludes Android.
Ordinary SSH connections through the userspace proxy remain possible. Desktop
system-tray integration is also omitted.

## Validation and limits

The release gate installs the Pacman package in a disposable native aarch64
Termux/Bionic container, starts an unauthenticated userspace daemon with temporary
state, exercises the CLI and Unix-socket JSON API, transfers synthetic HTTP bytes
through its local SOCKS5/HTTP proxies, changes a local preference and verifies it
after a process restart. The persistence check seeds a synthetic offline profile
with no login, node identity or keys, because upstream keeps a fresh profile in
memory until login. It does not join a tailnet, use real credentials,
change host DNS/routes/firewall, or claim an authenticated peer-to-peer tunnel
test. See the release's runtime evidence for the actual results.

Physical Android/SELinux restrictions, Android DNS service behavior, network
switches, battery/background survival and authenticated tailnet traffic require
device tests. Upstream's Android interface fallback reports a synthetic
interface when Android denies interface enumeration, so it cannot observe the
full interface picture. Container tests cannot establish that device behavior.

## Sources and licenses

Source: [upstream v1.104.2](https://github.com/tailscale/tailscale/tree/v1.104.2),
with its BSD-3-Clause license. The codeload archive SHA-256 is
`4c1c806e16507414a1459afcdc399f6a1323c21a1ac90f07bea0465fd8fd7e1d`.
The package preserves `go.mod`, `go.sum`, Go's license and actual dependency
license/notice files under `$PREFIX/share/doc/tailscale/`. The recipe pins Go
1.27.3 and retains the existing Termux Go runtime patches; automatic toolchain
replacement is disabled. No TUR recipe was used.

Upstream support details: [standalone Android feature](https://github.com/tailscale/tailscale/blob/v1.104.2/feature/androidbin/androidbin.go),
[Android DNS feature](https://github.com/tailscale/tailscale/blob/v1.104.2/feature/androiddns/androiddns.go),
[userspace networking](https://tailscale.com/kb/1112/userspace-networking).
