# Building and contributing

This guide covers repository maintenance. For installing packages on a device,
use the [repository setup instructions](../README.md#repository-setup). For key
provisioning and rotation, use the [maintainer signing guide](signing.md).

## Add or change packages

1. Add an upstream package name to [packages.json](../packages.json), or add a
   Termux-style recipe directory under `packages/NAME/` and list `NAME`. Entries
   are built in order; place custom dependencies before their consumers. The
   overlay directory name is the actual output package name. Use official
   Termux dependency names.
2. Pin each source version and checksum. For a modified official package that
   installs the same paths, use a distinct name, versioned `provides`, and
   explicit `conflicts`. Avoid automatic `replaces` unless migration requires it.
   Keep package-specific installation notes, conflicts, and limitations in its
   own README and link it from the root package list.
3. Review the package and runtime checks when changing the manifest or versions;
   the current checks include expectations for the selected packages. In
   particular, the WeeChat Python plugin must be rebuilt with a revision bump
   when the upstream Python ABI changes.
4. Add the package to a build matrix group in **Build and publish Pacman
   repository** and add its functional test to `scripts/runtime-test.sh`.
   Push to `main` or run the workflow manually. The combined build must cover
   the **entire package manifest**, including subpackages. Removing a manifest
   entry intentionally removes it from the next sync index.

Only selected recipes and their subpackages are indexed. Fallback builds of
official dependencies remain build inputs; the native runtime test resolves
those dependencies from the official repositories.

The [workflow](../.github/workflows/repository.yml) runs on pushes to `main`,
pull requests, and manual dispatch. Successful builds and runtime tests on
`main` can publish a release; pull requests do not publish. There is no docs path
filter. For a documentation-only push, include `[skip ci]` in the commit message
to [skip the push workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs);
do not manually dispatch a package build or release for documentation edits.
Skipped checks can remain pending where branch rules require them.

## Pinned inputs and build isolation

- [sources.json](../sources.json) pins the Termux-Pacman checkout and builder
  image by commit and digest; recipes pin source archives with SHA-256 hashes.
  The target is aarch64, Android/Bionic, and the standard Termux prefix. No
  host/glibc binaries are shipped.
- [prepare.py](../scripts/prepare.py) overlays the local recipes on the pinned
  upstream checkout and checks their dependency order. WeeChat's Android patches
  are preserved, with cJSON and headless support enabled.
- The [toolchain patch](../patches/no-fuse-toolchain.patch) uses a private NDK copy
  instead of the upstream FUSE overlay. It preserves the same compiler/sysroot
  without adding container capabilities or relaxing security profiles.
- Official dependencies are downloaded at the recipe's exact version and
  verified against signed upstream metadata. Unavailable versions are built by
  upstream's normal dependency machinery. Dependency versions and hashes are
  archived in the build evidence.
- Review upstream pin changes as toolchain and ABI changes, followed by a full
  build and runtime test.

Each workflow build gives selected recipes a unique Pacman revision
`1.RUN_NUMBER.RUN_ATTEMPT`. This avoids overwriting different bytes under a cached
package filename. Source/toolchain references are reproducible inputs, but this
does **not** claim independently verified bit-for-bit reproducibility: runner OS
packages and the availability of exact upstream binary dependencies can change.

## Local build

Use a Linux Docker host with Git and Python 3, from the repository root:

```sh
REPO_REVISION=1.1.1 bash scripts/build.sh
```

Use a fresh checkout/build directory for each build. The revision above is an
example; choose a new numeric revision for different package bytes.
[build.sh](../scripts/build.sh) prepares the pinned checkout, builds the manifest
in Docker, copies selected outputs to `dist/`, and runs the package verifier.
It does not perform the native runtime test or publish a release.

## Validation

Before starting the build matrix, the workflow runs the bounded launcher and
release-retention regression tests. Run these locally with Python 3 and GnuPG:

```sh
python3 -m unittest discover -s tests -p 'test_uptime_kuma_launcher.py' -v
python3 -m unittest discover -s tests -p 'test_release_retention.py' -v
```

These tests use temporary directories, a small runtime stand-in for the launcher,
and public signed bytes from the previous release; they create no signing keys.
The native runtime job also exercises the real Kuma launcher with a relative
data directory outside the package and checks database persistence after restart.

[verify-packages.py](../scripts/verify-packages.py) checks `.PKGINFO`, package
names, conflicts/provides, ELF architecture, the Android linker, and cJSON
linkage. The build also checks WeeChat's CMake feature switches. See the
[toot package notes](../packages/toot/README.md#package-validation) for its private
dependency and launcher checks.

The workflow's native aarch64 runner installs the packages in a disposable,
pinned Termux-Pacman container. It resolves dependencies from the official
repositories and checks WeeChat startup, the Python plugin, authenticated API
JSON, missing-password rejection, and a WeeChat API remote connection. It also
runs toot's offline checks.

The four service additions each have a package-local functional gate: Tailscale
exercises unauthenticated userspace proxies and persistent local preferences;
Uptime Kuma exercises its dashboard, a synthetic account and HTTP monitor
failure/recovery; AdGuard Home exercises high-port UDP/TCP DNS and persistent
rules; Vaultwarden exercises synthetic account/cipher APIs and SQLite restart.
All use disposable data and loopback services. The package verifier checks native
addons and `libexec` binaries as well as executables in `bin`. AdGuard Home and
Vaultwarden releases must include corresponding-source archives.

To reproduce the runtime job, use the container command and pinned image from
the [workflow](../.github/workflows/repository.yml) on a native aarch64 Docker
host with the built `dist/` artifacts. Do not run
[runtime-test.sh](../scripts/runtime-test.sh) directly on a user's device: it
upgrades and installs packages and is intended only for the disposable
container. It retains that image's signature policy, with local build artifacts
allowed by `LocalFileSigLevel=Optional` and signed upstream databases required.
This does not change the client setup's
`SigLevel = Required DatabaseRequired` policy.

These are **container tests, not tests on a physical Android device**. They use
temporary configuration without changing client settings. toot checks do not
use accounts or post to Mastodon. Consult the workflow and each release's
`build-evidence.tar.gz` for actual inputs, output metadata, and the runtime log.

## Publication and retained snapshots

Build and runtime jobs have read-only GitHub access. Only the final publication
job has `contents: write`, using the normal short-lived `GITHUB_TOKEN`; no PAT is
needed. Signing credentials are configured separately as described in the
[signing guide](signing.md).

1. [repository.py](../scripts/repository.py) uses `repo-add` to create
   `termux_repo-aarch64.db` and `.files`, plus compressed forms, and validates the
   machine-readable index.
2. [publish.sh](../scripts/publish.sh) signs packages and repository metadata
   when signing is configured. Signed releases include the public key,
   checksums, a machine-readable index, and build/runtime evidence.
3. Publication stages a **draft**, downloads the uploaded assets again, verifies
   checksums and the signed checksum manifest, then exposes the release. Only
   signed releases become `latest`. Missing or mismatched signing material after
   activation fails publication; it never downgrades the signed repository.

Previous package files, corresponding-source archives, and their verified
signatures are retained in new signed snapshots, so clients with an older cached
database can still fetch its packages
during an update. The current sync database indexes the current manifest. Old
release tags remain usable as pinned snapshots. Retention is intentionally
unbounded; plan explicit garbage collection if the repository grows large.
New corresponding-source filenames include the full package version and revision,
so rebuilding the same upstream version cannot replace an older package's source.
Previously published source filenames are retained unchanged.
