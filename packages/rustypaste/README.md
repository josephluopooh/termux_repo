# rustypaste 0.18.1

A small self-hosted paste service with expiry and authentication support. Uses Rustls; no background service is enabled automatically.

Native Android/Bionic aarch64 build from the pinned upstream source, with its
Cargo.lock enforced. Install after following the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/rustypaste
mkdir -p ~/rustypaste
cd ~/rustypaste
cp "$PREFIX/share/doc/rustypaste/config.toml" .
rustypaste
```

Upstream: https://github.com/orhun/rustypaste/tree/v0.18.1

License: MIT; the package retains the upstream license. Dependencies retain
their own licenses. See the release build evidence for ELF checks and native
Termux container test output. A container smoke test is not a physical-device
or full end-to-end interoperability test.
