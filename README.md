# termux_repo

A general-purpose **Pacman repository for Termux**, built by GitHub Actions and
hosted as complete, signed GitHub Release snapshots.

[Releases](https://github.com/josephluopooh/termux_repo/releases)
| [Builds](https://github.com/josephluopooh/termux_repo/actions/workflows/repository.yml)
| [Build and contribution guide](docs/building.md)
| [Maintainer signing guide](docs/signing.md)

## Compatibility

- **aarch64 only**, Android 7/API 24 or newer, Android **Bionic** libc.
- Standard `com.termux` prefix: `/data/data/com.termux/files/usr`.
- An existing [Termux-Pacman](https://github.com/termux-pacman/termux-packages)
  installation and its official `[main]` repository.
- Not an APT repository; not Arch Linux, proot Linux, Termux glibc, another
  application ID, or another CPU architecture. Check `uname -m` and `$PREFIX`.
- Remaining runtime dependencies resolve from the signed official Termux-Pacman
  repositories. Keep the full installation current; **partial upgrades are unsafe**.

## Repository setup

Keep signature verification enabled. Do not install unsigned build candidates
or disable signature checks to work around a failed verification.

1. Download `repository-key.asc` and `repository-key-fingerprint.txt` from the
   [latest signed release](https://github.com/josephluopooh/termux_repo/releases/latest).
   Inspect the downloaded key's **full 40-character primary fingerprint**:

   ```sh
   gpg --show-keys --with-fingerprint repository-key.asc
   ```

   Independently compare it and the release fingerprint file with the
   owner-reviewed [keys/fingerprint](keys/fingerprint), confirming the expected
   fingerprint through a trusted channel. Do not trust a key merely because it
   was downloaded beside the packages. Stop if the fingerprints do not match.

2. Import the verified public key into Pacman's keyring and locally sign it.
   Replace the placeholder with the full fingerprint you verified:

   ```sh
   pacman-key --add repository-key.asc
   pacman-key --lsign-key FULL_VERIFIED_40_CHARACTER_FINGERPRINT
   ```

3. Add this stanza to `$PREFIX/etc/pacman.conf`, **before `[main]`**, keeping all
   existing official repositories and their signature policies:

   ```ini
   [termux_repo-aarch64]
   SigLevel = Required DatabaseRequired
   Server = https://github.com/josephluopooh/termux_repo/releases/latest/download
   ```

## Install and update

Read the relevant [package notes](#packages) before installing, especially when
switching from an official package. Replace `PACKAGE_NAME` with a package below
and install it with a full upgrade:

```sh
pacman -Syu termux_repo-aarch64/PACKAGE_NAME
```

Review Pacman's dependency, conflict, and removal prompts. For later updates,
upgrade the whole installation:

```sh
pacman -Syu
```

## Packages

| Package | Purpose and documentation |
| --- | --- |
| `weechat-cjson` | [WeeChat with cJSON/API relay, headless support, and optional language plugins](packages/weechat-cjson/README.md). |
| `toot` | [Mastodon CLI and terminal interface](packages/toot/README.md). |
| `cjson` | JSON library used by WeeChat; see the [upstream documentation](https://github.com/DaveGamble/cJSON). |
| `terraria-server` | [Official vanilla Terraria downloader and native Mono launcher](packages/terraria-server/README.md). |
| `pumpkin-server` | [Upstream downloader and launcher for native Android Pumpkin](packages/pumpkin-server/README.md). |
| `tmodloader-server` | [Native .NET server setup and persistent worlds](packages/tmodloader-server/README.md). |
| `tshock-server` | [Native TShock server setup, administration and persistent state](packages/tshock-server/README.md). |
| `chisel` | [Authenticated TCP/UDP tunnels over HTTP](packages/chisel/README.md). |
| `ntfy` | [Notification CLI and HTTP API server; browser UI excluded](packages/ntfy/README.md). |
| `copyparty` | [File server with its browser interface](packages/copyparty/README.md). |
| `rainfrog` | [Database terminal interface](packages/rainfrog/README.md). |
| `presenterm` | [Markdown slides in the terminal](packages/presenterm/README.md). |

The owner selected these five additional applications. Other shortlist recipes
remain inactive under `candidates/`. Valheim is also requested; its remaining
[runtime restriction](docs/native-server-compatibility.md) keeps it outside
the publication manifest. `terraria-managed-support` is an application-local
dependency for tModLoader and TShock, using the official Termux .NET runtimes.

See [releases](https://github.com/josephluopooh/termux_repo/releases) for published
versions and [packages.json](packages.json) for the selected package manifest.

## Licensing

The infrastructure in `scripts/` and `.github/` is licensed under
[Apache License 2.0](LICENSE). Packages retain their upstream licenses:
Package guides include licenses, attribution, upstream links and any setup-time
downloads. Proprietary Terraria files are obtained directly from Re-Logic by
the user's explicit setup command; they are not redistributed in this repository.
