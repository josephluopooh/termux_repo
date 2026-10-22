# tModLoader 2026.08.3.0 native server

The release workflow requires installation, setup, world creation, protocol,
save and reload checks before publication. It uses official Termux `dotnet-runtime-8.0` and
`sdl2`, plus application-local MonoMod support. No proot, glibc, Linux
apphost or system-library replacement is used.

```sh
pacman -Syu termux_repo-aarch64/tmodloader-server
tmodloader-server install
tmodloader-server run -ip 127.0.0.1 -port 7777
```

The explicit install step downloads a checksum-pinned upstream release and
applies the compatibility changes locally. Pacman installation does not fetch
game files or start a server. Proprietary Terraria assemblies are not mirrored.
State and worlds persist under `$XDG_DATA_HOME/tmodloader-server/state`, or
`~/.local/share/tmodloader-server/state`. Upstream arguments follow `run`.
Use `-world /absolute/path/world.wld` for an existing world, or
`-config /absolute/path/serverconfig.txt` for an upstream configuration file.
The launcher uses `-tmlsavedirectory` to keep mods and saves independent of
the versioned downloaded program files. Put manually supplied `.tmod` files
and their `enabled.json` under the state's `Mods` directory.

This stable release targets Terraria 1.4.4.9. Steam/Workshop and graphical
startup are not enabled. Mods must be supplied manually. The adaptation skips
only the cosmetic CoreCLR stack-trace formatting hook and uses native SDL2.
Arbitrary mods and real player sessions still need validation.

The setup tool and launcher are Apache-2.0; upstream software keeps its own
licenses. Downloaded game files remain subject to their publisher's terms.
