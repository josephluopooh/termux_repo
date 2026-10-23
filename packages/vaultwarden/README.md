# Vaultwarden 1.37.4

Native aarch64 Android/Bionic build of the unofficial Bitwarden-compatible API
server, using the official Termux `libsqlite`, `openssl` and `ca-certificates`
packages. Install after the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/vaultwarden
vaultwarden
```

The launcher defaults to `http://127.0.0.1:8222`, disables registration,
invitations, push and icon downloads, and stores data in
`${XDG_DATA_HOME:-$HOME/.local/share}/vaultwarden` with a private umask. Nothing
starts at installation. Stop with Ctrl-C; run the same command to reopen the
same SQLite database. Back up the entire data directory while stopped,
including attachments and generated server signing keys.

This package is **API-only**. It deliberately ships no browser web vault and
does not claim a tested browser UI. Compatible Bitwarden clients can use a
custom server URL; client-version compatibility, real client encryption,
mobile connectivity, TLS, background survival on Android and real-device
operation remain untested. No account or actual vault data is used in CI.

Set environment variables explicitly to change the defaults, for example
`ROCKET_PORT=8223 vaultwarden`. `DATA_FOLDER` selects a different private data
directory. Registration can be enabled deliberately with
`SIGNUPS_ALLOWED=true vaultwarden` and disabled again after onboarding.
The admin interface remains disabled unless an administrator configures it.
Configuration saved by upstream in `DATA_FOLDER/config.json` can override
environment settings, so inspect existing configuration when reusing a data
directory. `ENV_FILE` defaults to `/dev/null` to avoid reading a caller's `.env`;
if explicitly set, its values do not override variables already exported by
the launcher. See `share/doc/vaultwarden/upstream.env.example` for upstream
settings. Exposing a password manager beyond localhost requires your own TLS,
authentication, backup and network configuration; the package changes none of
these settings and does not deploy a service.

The [official 1.37.4 source](https://github.com/dani-garcia/vaultwarden/tree/1.37.4)
is AGPL-3.0-only, pinned by SHA-256 and built with Rust 1.99.0,
`--no-default-features --features sqlite_system --profile release-low` for
`aarch64-linux-android`. It contains no glibc binary, bundled database server,
proot layer or TUR recipe. License texts and a dependency manifest are in
`$PREFIX/share/doc/vaultwarden`; each release also provides
`vaultwarden-1.37.4-source.tar.gz` with the corresponding source, locked crates,
and packaging files. Its `.cargo/config.toml` supports offline crate resolution.
Reproduce the Android build with this repository's pinned Termux framework and
builder as described in [building](../../docs/building.md), using the included
`termux-packaging` recipe. The official dynamic Termux libraries remain system
dependencies.

`python packages/vaultwarden/smoke-test.py` runs only with temporary directories
and loopback high ports. It checks default registration rejection and API
authentication, creates a synthetic `.invalid` account, logs in, stores and
updates an opaque synthetic cipher through the API, restarts the server, logs
in again, verifies synchronization and SQLite persistence, then deletes the
cipher. Generated test credentials, signing keys and data are removed. These
tests gate publication in the native aarch64 Termux container; they are not
physical Android hardware or end-to-end Bitwarden client tests.
