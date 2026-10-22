# ergo 2.19.1

IRC server with BuntDB, MySQL and PostgreSQL support. The optional modernc SQLite backend is excluded from this Android build. Copy the example configuration into a private directory and edit it before starting; no service is enabled automatically.

```sh
pacman -Syu termux_repo-aarch64/ergo
ergo --help
```

Built from https://github.com/ergochat/ergo/tree/v2.19.1 for Android/Bionic
aarch64 using Termux's patched Go toolchain. MIT license. Upstream dependency
licenses are preserved in the source; see release evidence for native runtime
checks. This is not a Linux/glibc executable.
