# rainfrog 0.4.6

Database exploration from the terminal; built with the upstream Termux feature set. DuckDB, Oracle and desktop clipboard integration are disabled.

Native Android/Bionic aarch64 build from the pinned upstream source, with its
Cargo.lock enforced. Install after following the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/rainfrog
rainfrog --url sqlite:///absolute/path/database.sqlite3
```

Upstream: https://github.com/achristmascarl/rainfrog/tree/v0.4.6

The recipe links SQLite from official `libsqlite` using
`LIBSQLITE3_SYS_USE_PKG_CONFIG=1`; CA certificates also come from the official
repository. It uses `--locked --no-default-features`, as upstream recommends
for Termux. Neither DuckDB, Oracle nor desktop clipboard libraries are bundled.

License: MIT. The package stages dependency notices and Cargo.lock under
`$PREFIX/share/doc/rainfrog`. TUR tree
`129d9f5e06a37f19313833b640d7bf0f7eb781f5` had no rainfrog recipe. This continues
the repository's existing candidate draft.

`python packages/rainfrog/smoke-test.py` creates a temporary SQLite database and
checks that rainfrog renders its table in a pseudo-terminal. The earlier
candidate passed cross-compilation in CI run 39815791199; this updated recipe
and native runtime still need the integration release gate. A container smoke
test is not a physical-device or remote-database interoperability test.
