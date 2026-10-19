# termux_repo

A general-purpose **Pacman repository for Termux**, built by GitHub Actions and
hosted as complete GitHub Release snapshots. The first custom package is
**`weechat-cjson` 4.10.1**, with cJSON, API relay, `/remote`, TLS, and the headless
binary enabled. cJSON is built and published alongside it. Lua, Perl, Python,
and Ruby plugins are separate `weechat-cjson-*-plugin` packages.

**`toot` 0.52.1** provides the Mastodon CLI and its built-in terminal interface.
Its hash-pinned pure-Python dependencies are packaged privately under `lib/toot`;
Pacman owns all installed files, with no runtime pip installs. Python and CA
certificates come from the official Termux-Pacman repository. Optional TUI image
libraries are not included. Upstream still includes `toot tui` in this release,
but marks it deprecated.

**Current publication status:** signed publication is configured. Keep signature
verification enabled and verify the public-key fingerprint as described below.
See [signing setup](docs/signing.md).

[Builds](https://github.com/josephluopooh/termux_repo/actions/workflows/repository.yml)
· [Releases](https://github.com/josephluopooh/termux_repo/releases)

## Compatibility

- **aarch64 only**, Android 7/API 24 or newer, Android **Bionic** libc.
- Standard `com.termux` prefix: `/data/data/com.termux/files/usr`.
- An existing **Termux-Pacman** installation and its official `[main]` repository.
- Not an APT repository; not Arch Linux, proot Linux, Termux glibc, another
  application ID, or another CPU architecture. Check `uname -m` and `$PREFIX`.
- Remaining runtime dependencies resolve from the signed official Termux-Pacman
  repositories. Keep the full installation current; partial upgrades are unsafe.

`weechat-cjson` provides the versioned `weechat` capability and conflicts with
`weechat`. Both install the `weechat` command and the same plugin paths, so they
are **alternatives, not coinstallable packages**. The custom name lets you keep
this build without a normal official WeeChat update replacing it. There is no
broad `replaces` declaration.

## Install after signed publication is enabled

1. Close WeeChat and back up `~/.config/weechat` (and `~/.weechat` if you use the
   legacy location). Switching packages does not remove these directories.
2. Obtain `repository-key.asc` and `repository-key-fingerprint.txt` from the
   signed release. Independently compare the **full 40-character fingerprint**
   with the owner-reviewed `keys/fingerprint` in this repository. Do not trust
   a key merely because it was downloaded beside the packages.
3. Import that verified public key into Pacman's keyring:

   ```sh
   pacman-key --add repository-key.asc
   pacman-key --lsign-key FULL_VERIFIED_40_CHARACTER_FINGERPRINT
   ```

4. Add this stanza to `$PREFIX/etc/pacman.conf`, before `[main]`, keeping all
   existing official repositories and their signature policies:

   ```ini
   [termux_repo-aarch64]
   SigLevel = Required DatabaseRequired
   Server = https://github.com/josephluopooh/termux_repo/releases/latest/download
   ```

5. Install with a full upgrade:

   ```sh
   pacman -Syu termux_repo-aarch64/weechat-cjson
   ```

   If official WeeChat is installed, review Pacman's conflict/removal prompt.
   Switch any installed language plugins in the **same transaction**, for example:

   ```sh
   pacman -Syu weechat-cjson weechat-cjson-python-plugin weechat-cjson-lua-plugin
   ```

   Use `pacman -Q | grep '^weechat'` to see which variants you have. Custom plugin
   packages conflict with their official counterparts and depend on the exact
   custom core version. The executable is still named `weechat`.

Update normally with `pacman -Syu`. To switch back, explicitly install official
`main/weechat` and the corresponding official plugins in one transaction, and
review the conflict prompts. Keep configuration backups: upstream versions may
migrate configuration formats.

Once the signed snapshot containing toot is published, install it using the same
repository configuration:

```sh
pacman -Syu termux_repo-aarch64/toot
toot --version
toot --help
toot tui --help
```

Use `toot login` or `toot login_cli` when you choose to connect your own account,
then `toot tui` to open the terminal interface. Packaging tests use offline help
commands and TUI rendering only; they do not log in or post to Mastodon.

## Verify the API

Inside WeeChat, use a new strong password and bind to localhost first:

```text
/set relay.network.bind_address 127.0.0.1
/set relay.network.password YOUR_OWN_STRONG_PASSWORD
/relay add ipv4.api 9000
```

Then, in another local terminal (curl prompts for the password):

```sh
curl --fail --user plain http://127.0.0.1:9000/api/version
```

A JSON response includes `weechat_version` and `relay_api_version`. Another
WeeChat instance can use `/remote add NAME URL -password=PASSWORD` followed by
`/remote connect NAME`. For access across a network use a properly configured
`tls.api` relay or a secure tunnel; localhost HTTP is only the local smoke test.
See the [WeeChat relay/API guide](https://weechat.org/files/doc/stable/weechat_user.en.html#relay_plugin)
and [API authentication](https://weechat.org/files/doc/weechat/stable/weechat_relay_api.en.html#authentication).

## Add packages

1. Add an upstream package name to `packages.json`, or add a Termux-style recipe
   directory under `packages/NAME/` and list `NAME`. Entries are built in order;
   place custom dependencies before their consumers. The overlay directory name
   is the actual output package name. Use official Termux dependency names.
2. Pin each source version and checksum. For a modified official package that
   installs the same paths, use a distinct name, versioned `provides`, and
   explicit `conflicts`. Avoid automatic `replaces` unless migration requires it.
3. Push to `main`, or run **Build and publish Pacman repository** manually.
   Every build uses the **entire package manifest**, including subpackages; adding
   a package requires no workflow edits and does not remove existing packages.
   Removing a manifest entry intentionally removes it from the next sync index.
   Only selected recipes and their subpackages are indexed. Fallback builds of
   official dependencies remain build inputs; the native runtime test resolves
   those dependencies from the official repositories.

Each build gets a unique Pacman revision `1.RUN_NUMBER.RUN_ATTEMPT` for selected
recipes. This avoids overwriting different bytes under a cached package filename.
Official dependencies are downloaded at the recipe's exact version and verified
against signed upstream metadata; unavailable versions are built by upstream's
normal dependency machinery. Dependency versions and hashes are archived in the
build evidence. Changes to the upstream pin should be reviewed as toolchain and
ABI changes, and followed by a full build and runtime test.

## Build, test, and release design

- `sources.json` pins the Termux-Pacman checkout and builder image by commit and
  digest; source archives have upstream SHA-256 hashes. WeeChat's Android patches
  are preserved, with cJSON and headless enabled. No host/glibc binaries are shipped.
- A small reviewed toolchain patch uses a private NDK copy instead of the
  upstream FUSE overlay. It preserves the same compiler/sysroot without adding
  container capabilities or relaxing security profiles.
- Build jobs have read-only GitHub access. Only the final publication job has
  `contents: write`, using the normal short-lived `GITHUB_TOKEN`. No PAT is needed.
- Builds verify `.PKGINFO`, package names, conflicts/provides, ELF architecture,
  Android linker, cJSON linkage, and the CMake feature switches.
- A native aarch64 runner installs the packages in a disposable pinned
  Termux-Pacman container, resolves dependencies, and checks API JSON, missing-
  password rejection, and a WeeChat API remote connection. This is a container
  test, **not a test on a physical Android device**. No client settings change.
- `repo-add` creates `termux_repo-aarch64.db` and `.files` plus compressed forms.
  Signed releases have package and metadata signatures, a public key, checksums,
  a machine-readable index, and build/runtime evidence.
- Publication stages a **draft**, downloads all uploaded assets again, verifies
  checksums/signatures, then exposes it. Only signed releases become `latest`.
- Previous package files are retained in new signed snapshots so clients that
  cached an older database can still fetch its packages during an update. Old
  release tags also remain usable as pinned snapshots. Retention is intentionally
  unbounded; plan explicit garbage collection if this repository grows large.
- The source/toolchain references are reproducible inputs, but this does not claim
  independently verified bit-for-bit reproducibility. Runner OS packages and the
  availability of exact upstream binary dependencies can still change.

To build locally on a Linux Docker host:

```sh
REPO_REVISION=1.1.1 bash scripts/build.sh
```

Use a fresh checkout/build directory for each build. See the workflow and release
`build-evidence.tar.gz` for the actual inputs, output metadata, and runtime log.

## Attribution and licensing

The WeeChat recipe, patches, and plugin split originate from
[Termux-Pacman's pinned source](https://github.com/termux-pacman/termux-packages/tree/7aae0e26de979162d09de28b05aaf3dd78592314/packages/weechat)
and are covered by WeeChat's GPL-3.0 license. cJSON is MIT-licensed. Other selected
packages retain their own licenses. The infrastructure in `scripts/` and
`.github/` is available under the Apache License 2.0; see [LICENSE](LICENSE).
