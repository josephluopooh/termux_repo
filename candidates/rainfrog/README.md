# rainfrog 0.4.6

Database exploration from the terminal; built with the upstream Termux feature set. DuckDB, Oracle and desktop clipboard integration are disabled.

Native Android/Bionic aarch64 build from the pinned upstream source, with its
Cargo.lock enforced. Install after following the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/rainfrog
rainfrog --url sqlite:///absolute/path/database.sqlite3
```

Upstream: https://github.com/achristmascarl/rainfrog/tree/v0.4.6

License: MIT; the package retains the upstream license. Dependencies retain
their own licenses. See the release build evidence for ELF checks and native
Termux container test output. A container smoke test is not a physical-device
or full end-to-end interoperability test.
