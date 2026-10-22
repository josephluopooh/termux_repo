# Valheim draft integration and verification

Status: **experimental draft; do not label as device-tested or release-ready**.
Only the integrator decides manifest selection and publication. This work adds
the Valheim package directory, its tests, and these notes. It does not edit the
main workflow, root README, package selection, shared checkout, or signing setup.

## Verified inputs

The actual Pacman repositories were read from
`https://service.termux-pacman.dev/{main,gpkg}/aarch64/`. Both database signatures
and the seven downloaded package signatures verified against the key committed
in pinned Termux-Pacman source `7aae0e26de979162d09de28b05aaf3dd78592314`:
`998DE27318E867EA976BA877389CEED64573DFCA`. Package SHA-256 values also matched
their signed database entries. See the adjacent `valheim-upstream-audit.json`.

| Repository | Package | Audited version | Purpose |
| --- | --- | --- | --- |
| gpkg | box64-glibc | 0.4.4-0 | AArch64 glibc Box64; also supplies x86_64 support libraries |
| gpkg | glibc | 2.44-0 | `glibc/lib/ld.so`, libc |
| gpkg | gcc-libs-glibc | 14.2.1-1 | `libatomic.so.1`, native `libstdc++.so.6` |
| gpkg | libpulse-glibc | 17.0-1 | `libpulse.so.0` |
| gpkg | libogg-glibc | 1.3.6-0 | `libogg.so.0` |
| gpkg | glibc-runner | 2.0-3 | Audited only; wrapper uses explicit loader to preserve argv |
| main | dotnet-runtime-9.0 | 9.0.21-0 | Native Android .NET for the managed downloader |

Dependency-name closure for those seven roots found 136 available packages and
no missing names across the downloaded main/gpkg databases. This is **not a
Pacman solver transaction**: version/conflict resolution, extraction, install
hooks, and execution still require the container/device acceptance step. In
particular, `libpulse-glibc` also depends on official Bionic `pulseaudio`. The
wrapper itself does not start PulseAudio or change service settings; upstream
package installation hooks were not exercised here.

No SDL-named glibc package is present in that gpkg snapshot. Ogg is present.
The Box64 executable is AArch64 (ELF machine 183); its bundled guest libstdc++
is x86_64 (machine 62) and includes GLIBCXX_3.4.34. The native GCC libstdc++
also includes GLIBCXX_3.4.34, exceeding Iron Gate's documented 3.4.26 minimum.
The application payload was not downloaded or executed in this task, so its
complete current DT_NEEDED/dlopen dependency graph remains unaudited.

DepotDownloader 3.4.0's official framework archive was downloaded and hashed.
Its runtimeconfig requests `net9.0` / Microsoft.NETCore.App 9.0.0; its dependency
manifest contains managed SteamKit2 3.2.0, protobuf-net, System.IO.Hashing,
QRCoder, and ZstdSharp.Port assemblies. It does not require an emulated x86
SteamCMD. This is archive inspection, not a native Android .NET execution test.

TUR was inspected at `129d9f5e06a37f19313833b640d7bf0f7eb781f5`. It has a current
`tur/depotdownloader/build.sh` using .NET 9 and `UseAppHost=false`, no Valheim or
Box64 recipe in that tree. The existing recipe corroborates the managed approach.
No TUR implementation was copied; its package recipes follow their package
licenses (DepotDownloader: GPL-2.0). A future standalone downloader package can
reuse it with proper source/license retention.

## Local tests

Run from this repository:

```sh
python -m unittest discover -s tests -p test_valheim_server.py -v
bash -n packages/valheim-server/build.sh
bash tests/test_valheim_recipe.sh
```

The final Windows run: 18 tests, 17 passed, one skipped (real POSIX flock).
Tests are network-free and substitute downloader/runtime calls. They cover
informational terms notices without an invented acceptance gate, checksum rejection, archive traversal/symlinks,
payload architecture/shape, atomic updates, preservation of config/worlds on
failure, anonymous Linux/64 arguments, quoted arguments, environment separation,
bad config, pointer traversal, and absence of implicit package installation.
They do not claim a real game launch, connectivity, or physical Android test.
The pinned upstream `scripts/buildorder.py -i` accepted the recipe against its
Bionic package trees. The recipe install smoke test also passes: exactly the
launcher and README are installed, and the launcher is executable. This is not
a full Termux cross-build or generated Pacman archive validation.

## Integration

1. Apply the supplied Valheim-only patch. Decide whether to stage it outside the
   published manifest until the checks below pass. No workflow changes are
   included in the patch.
2. Run the existing pinned Termux dependency parser and package builder for
   `valheim-server`. Standard Bionic dependencies are declared normally. The
   separate gpkg runtime is in `TERMUX_PKG_SUGGESTS`, with mandatory launcher
   checks and a complete install command in the package README.
3. Package verification should require only our text launcher/docs, no `.INSTALL`
   script, no ELF or proprietary/managed application payload. The launcher mode
   is 0755. Add the test command above to the existing smoke mechanism, not a
   second publishing workflow.
4. In the existing disposable aarch64 Termux-Pacman test environment, enable the
   official signed gpkg repository and perform a full-upgrade transaction:
   `pacman -Syu valheim-server box64-glibc glibc gcc-libs-glibc libpulse-glibc libogg-glibc`.
   Preserve the resolved package/version/signature evidence and run `doctor`.
   Do not weaken signature checks. This is a pending validation, not a claim
   that the transaction has already succeeded.
5. Test `dotnet DepotDownloader.dll` using the pinned framework archive without
   downloading the game (usage output). Ensure the native Android .NET runtime
   can initialize networking and its managed dependencies. Passing this does
   not establish anonymous depot availability or server launch.
6. Run the authorized setup/download tests in the target environment and
   preserve Steam manifests. There is no observed upstream legal-acceptance
   blocker: the downloader was not executed here. Its pinned source's anonymous
   path calls `LogOnAnonymous()` without a legal-acceptance prompt in the inspected
   code. The original draft's typed agreement gate was our own unnecessary
   addition and has been removed. If a real upstream agreement prompt appears,
   stop and ask the user about that exact action; do not answer it automatically.
   Audit resulting ELF/library errors, especially SDL3, before adding packages.
7. Start only with user authorization for network service execution. Verify
   `Game server connected`, a client join, save/restart, graceful Ctrl+C, a failed
   update retaining the old build, and configuration persistence. Keep crossplay
   disabled pending the upstream Box64 regression. Container success alone must
   be labeled as a container test, not an Android-device result.

## Corrected blocker record

The earlier statement that an explicit acceptance action blocked game download
was an inference from Valheim EULA section 1.2, not an observed downloader prompt.
That section describes agreement through downloading/installing/using the game;
it does not establish a mandatory checkbox or typed prompt in DepotDownloader.
No official download/setup command was run and no legal prompt was encountered.
No action was denied or has an uncertain execution outcome.

The actual limitation is the Windows workspace: `dotnet`, `pacman`, and `docker`
are absent from PATH, and the standard Termux prefix is absent. The aarch64
Termux package transaction, native .NET execution, and game startup are therefore
pending in the integrator's target test environment. Source inspection and the
signed binary/metadata audit do not replace those runtime tests.

Source inspection covered DepotDownloader 3.4.0's `Program.cs`, `Steam3Session.cs`,
and `ContentDownloader.cs`. Credential/2FA prompts belong to authenticated login;
our command supplies no username/password/QR option. Legal-reference links are
informational, not a claim that the tool presented an acceptance request:
[Valheim EULA](https://www.valheimgame.com/eula/) and
[Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/).

## Primary sources

- [Iron Gate dedicated server guide](https://www.valheimgame.com/support/a-guide-to-dedicated-servers/)
- [Valheim EULA](https://www.valheimgame.com/eula/)
- [Termux glibc Box64 recipe](https://github.com/termux/glibc-packages/blob/main/gpkg/box64/build.sh)
- [Pacman gpkg repository](https://github.com/termux-pacman/glibc-packages)
- [glibc-runner behavior](https://github.com/termux-pacman/glibc-packages/wiki/About-glibc-runner-%28grun%29)
- [DepotDownloader usage](https://github.com/SteamRE/DepotDownloader/tree/DepotDownloader_3.4.0)
- [DepotDownloader anonymous login source](https://github.com/SteamRE/DepotDownloader/blob/DepotDownloader_3.4.0/DepotDownloader/Steam3Session.cs#L424-L429)
- [Box64 crossplay report #4403](https://github.com/ptitSeb/box64/issues/4403)
