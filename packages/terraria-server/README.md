# Official Terraria dedicated server 1.4.5.8

This is the **standard, unmodified Re-Logic Terraria server**, separate from
TShock. The Pacman package contains only this repository's downloader/launcher;
it does not redistribute the proprietary game/server files. `install` fetches
the official archive over HTTPS and checks its pinned SHA-256 before installation.

```sh
pacman -Syu termux_repo-aarch64/terraria-server
terraria-server install
terraria-server run -lang 1
```

The archive's Linux native host is **x86-64**, not ARM64. This launcher instead
uses the unmodified managed TerrariaServer.exe and FNA.dll with official Termux
**native Mono**, not proot, glibc or CPU emulation. The filename `.exe` here is a
managed .NET assembly, not a promise of Windows emulation. Native dependencies
come from official `mono` and `mono-libs` packages.

Files live under `${XDG_DATA_HOME:-$HOME/.local/share}/terraria-server/1.4.5.8`;
worlds default to the adjacent `worlds` directory. Pacman uninstall does not
delete worlds. Pass normal upstream arguments after `run`, for example
`-world /absolute/path/example.wld -autocreate 1 -port 7777 -maxplayers 8`.
Stop with the console `exit` command to save your world. Match the client/server
versions; crossplay is not asserted by this package.

- [Official download](https://terraria.org/api/download/pc-dedicated-server/terraria-server-1458.zip)
- Archive SHA-256: `f513a4ac9789d34af766291ae217c9cd7d9472e13782a0e2b17512f70d7a8334`
- Launcher: Apache-2.0. Server: proprietary Re-Logic software, obtained directly
  by the user and subject to upstream terms.

No server starts and no proprietary content is downloaded during Pacman install.
See release evidence for actual startup/world/network tests and their limits.
