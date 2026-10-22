# TShock 6.2.1 native server draft

This package is not in the publication manifest until its complete setup and
runtime checks pass. It uses official Termux `dotnet-runtime-9.0` and
`libsqlite`, plus application-local MonoMod support. No proot, glibc, Linux
apphost or system-library replacement is used.

```sh
tshock-server install
tshock-server run -ip 127.0.0.1 -port 7777
```

The explicit install step downloads a checksum-pinned upstream release and
applies the compatibility changes locally. Pacman installation does not fetch
game files or start a server. Proprietary Terraria assemblies are not mirrored.
State and worlds persist under `$XDG_DATA_HOME/tshock-server/state`, or
`~/.local/share/tshock-server/state`. Upstream arguments follow `run`.

TShock targets Terraria 1.4.5.8 and is distinct from the official vanilla
`terraria-server` package. The adaptation installs constructor hooks before game
table initialization and uses official SQLite through its standard C ABI.
Plugin compatibility and player sessions still need validation.

The setup tool and launcher are Apache-2.0; upstream software keeps its own
licenses. Downloaded game files remain subject to their publisher's terms.
