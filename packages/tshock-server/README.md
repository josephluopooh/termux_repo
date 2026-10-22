# TShock 6.2.1 native server

This package uses official Termux `dotnet-runtime-9.0` and `libsqlite`, plus
application-local MonoMod support. No proot, glibc, Linux apphost or system
library replacement is used. It targets Terraria 1.4.5.8.

```sh
pacman -Syu termux_repo-aarch64/tshock-server
tshock-server install
tshock-server run -ip 127.0.0.1 -port 7777
```

The explicit install step downloads checksum-pinned upstream archives and
applies the compatibility changes locally. Pacman installation does not fetch
game files or start a server. Proprietary Terraria assemblies are not mirrored.
Upstream arguments follow `run`; use `exit` in the server console to save and stop.

State persists under `$XDG_DATA_HOME/tshock-server/state`, or
`~/.local/share/tshock-server/state`. Worlds are under `worlds/`, TShock's
configuration and SQLite database under `tshock/`, logs under `logs/`, and user
plugins under `ServerPlugins/`. The built-in TShock plugin remains with the
versioned application. Existing world paths, including spaces, are accepted
with `-world /absolute/path/to/world.wld`.

The adaptation installs constructor hooks before game-table initialization,
uses official SQLite through its standard C ABI, and replaces the upstream
ARM64 archive's reference-only Steamworks.NET assembly with the pinned real
managed implementation from official NuGet 2024.8.0. Its IL-only architecture
metadata is adapted to AnyCPU; native Steam APIs remain disabled. The source
URLs, hashes, change notice and MIT copyright notice are retained under the
installation's `licenses/` directory.

Actual Pacman installation, explicit/idempotent setup, valid Terraria protocol
handshake and world information, wrong-version rejection, world save/reload,
clean exit, and persistent SQLite administration commands pass in native
aarch64 Termux Bionic userspace. Physical Android devices, real player sessions
and third-party plugins remain untested.

The setup tool and launcher are Apache-2.0. TShock and downloaded dependencies
retain their own licenses; game files remain subject to their publisher's terms.
