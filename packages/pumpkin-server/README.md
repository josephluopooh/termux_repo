# Pumpkin 0.2.0 (Java 26.3 / Bedrock 26.51)

This package downloads Pumpkin's official **aarch64-android** release on explicit
setup. Upstream builds it with NDK r27c and Android API 24. It is a native Bionic
executable; Java and proot are not required. The immutable release binary is
checked against its SHA-256 before installation.

```sh
pacman -Syu termux_repo-aarch64/pumpkin-server
pumpkin-server install
mkdir -p ~/servers/pumpkin
cd ~/servers/pumpkin
pumpkin
```

Read and follow the Minecraft EULA linked by upstream. No EULA is accepted by
the package, and no server starts during installation. Configuration and worlds
are stored in your working directory. Back up existing worlds before testing.

This is an independent Rust implementation in active development, not the Mojang
server, Paper, or a guarantee of vanilla feature parity. Core multi-version Java
support was removed in 0.2.0; older clients need the separate upstream plugin.
Upstream targets **Java 26.3 and Bedrock 26.51** in this pinned release. Plugins and
all gameplay features have not been exhaustively tested by this repository.

- [Release](https://github.com/Pumpkin-MC/Pumpkin/releases/tag/0.2.0%2B26.3-26.51)
- [Source](https://github.com/Pumpkin-MC/Pumpkin/tree/204a94ed895f041a845630d5a23c094705a0704e)
- [Documentation](https://docs.pumpkinmc.org/)

The launcher is Apache-2.0. Pumpkin's original code is GPL-3.0, but its
[asset notice](https://github.com/Pumpkin-MC/Pumpkin/blob/204a94ed895f041a845630d5a23c094705a0704e/assets/NOTICE.md)
excludes Mojang-derived game data from that license. This repository therefore
does not mirror the upstream payload or asset-containing source archive. Setup
downloads directly from upstream; no content is fetched during Pacman install.
The executable lives under `${XDG_DATA_HOME:-$HOME/.local/share}/pumpkin-server/`;
configuration and worlds stay in the working directory and survive package updates.

See build-evidence.tar.gz for exact ABI and runtime checks; those checks run in a
Termux container, not on a physical phone.
