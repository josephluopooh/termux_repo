# rathole 0.5.0

A compact reverse tunnel with client/server and Noise support. This embedded feature set excludes TLS and WebSocket transports; use Noise for encrypted tunnels.

Native Android/Bionic aarch64 build from the pinned upstream source, with its
Cargo.lock enforced. Install after following the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/rathole
rathole server.toml
```

Upstream: https://github.com/rathole-org/rathole/tree/v0.5.0

License: Apache-2.0; the package retains the upstream license. Dependencies retain
their own licenses. See the release build evidence for ELF checks and native
Termux container test output. A container smoke test is not a physical-device
or full end-to-end interoperability test.
