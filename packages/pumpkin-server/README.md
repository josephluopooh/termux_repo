# Pumpkin 0.2.0 (Java 26.3 / Bedrock 26.51)

This package contains Pumpkin's official **aarch64-android** release, built upstream
with NDK r27c and Android API 24. It is a native Bionic executable; Java and proot
are not required. The immutable release binary is checked against its SHA-256.

```sh
pacman -Syu termux_repo-aarch64/pumpkin-server
mkdir -p ~/servers/pumpkin
cd ~/servers/pumpkin
pumpkin
```

Read and follow the Minecraft EULA presented by upstream. No EULA is accepted by
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

GPL-3.0. The matching source archive, including locked dependency sources and
licenses plus Cargo's offline source configuration, is included as a release
asset. This source bundle does not add dependency packages to your repository.
See build-evidence.tar.gz for exact ABI and
runtime checks; those checks run in a Termux container, not on a physical phone.
