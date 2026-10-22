# Package selection and dependency policy

The requested servers are official vanilla Terraria, TShock, Pumpkin,
tModLoader and Valheim. The owner selected exactly five additional applications:
chisel, ntfy, copyparty, rainfrog and presenterm. Other shortlist recipes under
`candidates/` remain outside the build and publication manifest.

| Selected application | Version | Intentional feature choice |
| --- | --- | --- |
| chisel | 1.12.0 | Authenticated TCP/UDP tunnels over HTTP |
| ntfy | 2.32.0 | Notification CLI and HTTP API server; no browser UI |
| copyparty | 1.20.26 | File server including its browser interface |
| rainfrog | 0.4.6 | SQLite/PostgreSQL/MySQL TUI; no DuckDB, Oracle or desktop clipboard |
| presenterm | 0.16.1 | Text slides; graphics/PDF features are not validated |

The official source-tree check used
`termux/termux-packages@facb27bc85ef36fd1120d4ae990fbd59e134fc61`, alongside
the live aarch64 main/root/X11 indexes and package aliases. TUR is a separate
repository, not an official Termux dependency provider. Reused TUR work retains
its attribution and license notices in the corresponding package directory.
Builds use this repository's pinned Termux-Pacman checkout from `sources.json`;
runtime checks resolve dependencies from its official signed Pacman repositories.

## Reuse official dependencies

The pre-existing cJSON, WeeChat and toot packages remain intact. Native Mono,
.NET, Python, SQLite, SDL2, OpenSSL, zlib, oniguruma and other available runtime
libraries come from official Termux packages. Build-only fallback dependencies
are recorded as evidence and are not copied into the published package index.
The managed servers need application-local Bionic MonoMod support because the
upstream Android backend is unimplemented. This does not replace system libraries.

Rust and Go applications compile their normal source dependencies using
upstream lockfiles/checksums and retain dependency copyright/license notices.
They are not separate private Pacman system packages. Copyparty's unavailable
Jinja2/MarkupSafe dependencies are private to that application; runtime pip
installation is not used. The existing toot dependency layout is unchanged.

## Server publication gates

Vanilla Terraria and Pumpkin use checksum-pinned downloads directly from their
publishers during an explicit setup command. Mixed-license game payloads are
not mirrored here. TShock and tModLoader require native Mono/.NET runtime and
packaged-launcher checks before activation. Valheim is an accepted glibc/Box64
exception, with anonymous on-phone Steam download and no PC transfer, but still
needs a working server runtime. No package uses proot.

See [the compatibility evidence and remaining limits](native-server-compatibility.md).
The signed release index is authoritative for available packages.
