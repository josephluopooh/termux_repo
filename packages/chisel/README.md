# chisel 1.12.0

SSH-encrypted tunnel over HTTP. Run `chisel server --help` and `chisel client --help` for explicit listener and authentication settings.

```sh
pacman -Syu termux_repo-aarch64/chisel
chisel --help
```

Built from https://github.com/jpillora/chisel/tree/v1.12.0 for Android/Bionic
aarch64 using Termux's patched Go/Clang toolchain. Version 1.13 is a prerelease
and is not selected. HTTPS uses the official `ca-certificates` package.

MIT license; the upstream license, Go license, dependency notices and module
lock files are staged under `$PREFIX/share/doc/chisel`. TUR tree
`129d9f5e06a37f19313833b640d7bf0f7eb781f5` had no Chisel recipe. This recipe
continues the repository's existing candidate draft.

`python packages/chisel/smoke-test.py` verifies an authenticated loopback tunnel
by transferring an HTTP payload. The release workflow requires this test in
a native aarch64 Termux container after Pacman installation. No service starts
during package installation. Physical-device networking is a separate check.
