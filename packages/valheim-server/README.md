# Valheim server for Termux-Pacman — experimental draft

This package contains our launcher only. It downloads the official Linux x86_64
dedicated server **on the phone**, anonymously from Steam, when you run `setup`.
No desktop Steam installation, account, password, PC download, or manual upload
is needed for the intended public-depot path. A reusable official whole-server
ZIP URL has not been identified: Steam distributes the content using manifests
and chunks. DepotDownloader handles that protocol.

The server uses the existing **glibc Box64** package to translate its Unity
x86_64 engine. It does not use proot, a container, Wine, or native Mono. Mono
alone cannot execute Unity's native x86_64 engine. This draft has wrapper tests
and signed package audits, **not a successful Android server startup test**.

## Install

Requires aarch64, the standard `/data/data/com.termux/files/usr` prefix, and
Termux-Pacman. Keep the entire installation current. Do not mix APT packages,
Arch packages, or Bionic libraries into the glibc directory.

The native Python, CA certificates, and .NET 9 runtime resolve from `[main]`.
The glibc runtime resolves from the existing Termux-Pacman `[gpkg]` repository.
No runtime dependency tree is mirrored into this custom repository.

If `[gpkg]` is not already configured, review the
[upstream repository instructions](https://github.com/termux-pacman/glibc-packages)
and add its stanza to your own `$PREFIX/etc/pacman.conf`:

```ini
[gpkg]
SigLevel = Required DatabaseRequired
Server = https://service.termux-pacman.dev/gpkg/$arch
```

Use the existing official Termux-Pacman keyring. Do not disable verification or
import a key just because a download failed. The audited signer was
`998DE27318E867EA976BA877389CEED64573DFCA`, matching this repository's pinned
upstream key. The launcher never edits Pacman configuration or keyrings.

After the integrator has published this package, install in one full-upgrade
transaction:

```sh
pacman -Syu valheim-server box64-glibc glibc gcc-libs-glibc libpulse-glibc libogg-glibc
valheim-server doctor
valheim-server setup
valheim-server start
```

The glibc packages are declared as suggested dependencies because the existing
Bionic build graph cannot resolve recipes from the separate `gpkg` tree. They
are **required for setup/start**, and the launcher checks them. Use the complete
install command above. This recipe does not change the main build workflow.

`setup` asks for a server name, world name, and password. It displays the current
[Valheim EULA](https://www.valheimgame.com/eula/) and
[Steam terms](https://store.steampowered.com/subscriber_agreement/) links.
No explicit legal-acceptance prompt was found in the inspected DepotDownloader
3.4.0 anonymous download path; the launcher adds no agreement checkbox or typed
acceptance. It supplies no answers or acceptance flags to upstream prompts.
If an actual agreement prompt appears during testing, stop and obtain the user's
decision. No Steam credentials are collected or saved by this launcher.

## Normal use

```sh
valheim-server start   # foreground; Ctrl+C requests a graceful save/stop
valheim-server update  # stop first; explicitly download the current public build
valheim-server paths  # show persistent locations
```

`start` does not download or update anything. `setup` is idempotent once an
installation exists. `update` downloads to a new directory and changes the
current pointer only after the downloader
succeeds and the required x86_64 ELF files are present. A failed update preserves
the active server, config, and worlds. Older game directories are retained;
they can be large. No automatic cleanup or downgrade is performed.

Default locations (honor absolute `XDG_CONFIG_HOME` / `XDG_DATA_HOME` overrides):

| Content | Location |
| --- | --- |
| Private JSON config | `~/.config/valheim-server/config.json` |
| Worlds and admin/ban/permission lists | `~/.local/share/valheim-server/worlds/` |
| Unity log files | `~/.local/share/valheim-server/logs/` |
| Server generations / Steam manifests | `~/.local/share/valheim-server/gen-*/` |
| Active download record | `~/.local/share/valheim-server/current.json` |

Stop the server before editing config, updating, or backing up worlds. Preserve
the whole `worlds` directory. Package removal does not remove these user files.
New config files are private (0600), and names/passwords are passed as separate
arguments, never evaluated as shell text. The game requires its password in the
process arguments; it may be visible to other processes with sufficient access.

The JSON fields are `name`, `world`, `password`, `port`, `public`, and `crossplay`.
The default is port 2456 (Valheim also uses port+1), `public: false`, and
`crossplay: false`. **`public: false` only hides the server list entry; it is not
a loopback bind or firewall.** Starting the game can listen on network interfaces
and contact Steam. Installation/setup do not start the server, expose ports,
enable autoboot, or alter firewall/router settings.

Crossplay is rejected in this draft because upstream reports PlayFab/join-code
registration failures with Box64 0.4.4:
[Box64 issue #4403](https://github.com/ptitSeb/box64/issues/4403).
Steam-only gameplay still needs actual device validation.

## Runtime and diagnostics

The launcher invokes `$PREFIX/glibc/lib/ld.so` with
`$PREFIX/glibc/bin/box64` and a separate glibc library search path. This is the
explicit-loader approach described by
[glibc-runner](https://github.com/termux-pacman/glibc-packages/wiki/About-glibc-runner-%28grun%29).
It avoids `grun 2.0`'s unquoted argument expansion for names/passwords containing
spaces. `glibc-runner` itself is not required. Bionic `LD_PRELOAD` is removed only
from child environments; no global shell settings or ELF files are patched.
Box64's packaged x86_64 support libraries and the game's `linux64` directory are
included in `BOX64_LD_LIBRARY_PATH`.

`doctor` checks architecture, prefix, Pacman package registration, runtime files,
and the installed payload's ELF headers. It is a preflight check, not a proof
that native library wrapping, Unity, Steam networking, or client joins work.

Iron Gate documents GLIBC 2.29, GLIBCXX 3.4.26, libatomic, and PulseAudio needs.
The signed `[gpkg]` packages provide the relevant glibc, GCC, PulseAudio, and Ogg
files. No SDL package was found in the audited `[gpkg]` database. A server build
that needs unbundled SDL3 or another unsupported library may still fail; read
Box64's terminal output and the Unity log before adding a dependency. The draft
does not fetch arbitrary third-party shared libraries as a fallback.

The downloader archive is pinned to SteamRE DepotDownloader 3.4.0 with SHA-256
`7419f65efb7eb16b6e56987ed1b76475f29c02475c0016166c84798388e796bc`.
Its runtime config is `net9.0`; the README's .NET 8 statement is stale.
The **game payload follows Steam's current public branch**, not a fixed version.
DepotDownloader verifies Steam content; manifests and a local download record
are retained. There is no independently pinned whole-game SHA-256 in this draft.

## Licensing and provenance

Our recipe and launcher are Apache-2.0 under the repository license. No game,
Unity, Steam runtime, Mono, .NET, Box64, or DepotDownloader binaries are included
in the Pacman package. Valheim remains governed by its own EULA; section 5.2.1
restricts sharing copies. Downloads go directly to the user's device from Steam.

The downloaded DepotDownloader archive includes its upstream GPL-2.0 license;
the wrapper preserves it. Source is available at
[SteamRE's 3.4.0 tag](https://github.com/SteamRE/DepotDownloader/tree/DepotDownloader_3.4.0).
The [TUR recipe](https://github.com/termux-user-repository/tur/blob/129d9f5e06a37f19313833b640d7bf0f7eb781f5/tur/depotdownloader/build.sh)
was inspected: it already builds 3.4.0 as a framework-dependent .NET 9 assembly
with `UseAppHost=false`. No TUR code was copied into this independently written
launcher. If a later revision packages that recipe, preserve its GPL-2.0 terms
and corresponding source obligations instead of relabeling it Apache-2.0.

Maintainer verification and remaining acceptance checks are recorded in
`docs/valheim-draft-audit.md` in the source repository.
