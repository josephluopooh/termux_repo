# ntfy 2.32.0

HTTP notification client and native Android/Bionic API server for aarch64.
Install after the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/ntfy
ntfy serve
# In another terminal:
ntfy publish http://127.0.0.1:8080/example 'Hello Termux'
ntfy subscribe --poll http://127.0.0.1:8080/example
```

The packaged `$PREFIX/etc/ntfy/server.yml` binds to loopback port 8080 and
disables the web UI. Messages use an in-memory cache by default; configure an
absolute `cache-file` path in your Termux home for persistence. No service is
started at installation. Set authentication and your intended bind address
before allowing other devices to connect. Android may suspend background apps.

This is the CLI/API build supported by upstream's Makefile. The browser web app
and offline documentation are not built; no Node.js runtime is required. HTTP
publish/subscribe and the server are included. Optional integrations such as
Firebase, SMTP, payments, and browser push have not been runtime-tested here.
Desktop notification hooks require an appropriate command; this package does
not install or configure Termux:API.

Build dependencies use the repository's pinned Termux Go/Clang toolchains.
Runtime SQLite and CA certificates come from the official `libsqlite` and
`ca-certificates` packages. Go modules are pinned by `go.mod`/`go.sum`; no Go
toolchain is required at runtime. Configuration and subscriber shell paths are
patched for `$PREFIX`. The source patch carries the modification notice.

[Upstream source](https://github.com/binwiederhier/ntfy/tree/v2.32.0) is dual
Apache-2.0/GPL-2.0; this package uses the Apache-2.0 option and retains both
upstream license texts. Dependency license files and the Go license are staged
under `$PREFIX/share/doc/ntfy`. TUR tree
`129d9f5e06a37f19313833b640d7bf0f7eb781f5` contained no ntfy recipe.

`python packages/ntfy/smoke-test.py` checks a loopback CLI publish/poll and a live
HTTP subscription, then restarts the server and checks SQLite persistence.
Run in a disposable native aarch64 Termux environment after installing the
package. These checks gate publication in the repository's release workflow.
