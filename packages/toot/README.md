# toot

The Mastodon command-line client and its built-in terminal interface, packaged
for this [Termux-Pacman repository](../../README.md). The [recipe](build.sh),
[dependency lock](requirements.txt), and
[releases](https://github.com/josephluopooh/termux_repo/releases) define the
packaged versions. See the [upstream documentation](https://toot.bezdomni.net/)
for commands, authentication, and general usage.

## Packaging notes

- Hash-pinned pure-Python dependencies are installed at build time under the
  private `$PREFIX/lib/toot` directory, with their metadata and licenses.
  Pacman owns the installed files; there are no runtime pip installs.
- The `toot` launcher uses those private dependencies independently of pip and
  user site packages. Python and CA certificates come from the official
  Termux-Pacman repository; the bundled certifi uses the official CA bundle at
  `$PREFIX/etc/tls/cert.pem` and receives its normal security updates.
- **Optional TUI image libraries are not included**, so their image features
  are unavailable in this package.
- The upstream version selected by the recipe still includes `toot tui`, but
  marks it **deprecated**. Do not assume the TUI will remain in future versions.

## Install and check

Complete the [signed repository setup](../../README.md#repository-setup), then:

```sh
pacman -Syu termux_repo-aarch64/toot
toot --version
toot --help
toot tui --help
```

Keep the full installation current with `pacman -Syu`.

When you choose to connect your own account, follow the upstream authentication
instructions using `toot login` or `toot login_cli`; `toot tui` opens the terminal
interface. The version and help commands above do not log in or post to Mastodon.

## Package validation

The repository's [package verifier](../../scripts/verify-packages.py) checks the
launcher, private dependency metadata against the lock file, CA-bundle symlink,
and absence of runtime install hooks, global site packages, or native binaries.

The [offline smoke test](../../scripts/toot-smoke-test.py), invoked by the
[runtime test](../../scripts/runtime-test.sh), uses temporary configuration and
blocks network access. It checks CLI/TUI help, private dependencies, the system
CA bundle, and TUI construction and rendering at 80 by 24 characters. It verifies
that optional image support is disabled. It does not run the interactive network
session, log in, or post to Mastodon.

See [build and test instructions](../../docs/building.md#validation) for the
disposable container environment and its limits.

## Licensing

toot is GPL-3.0; see the [upstream project](https://github.com/ihabunek/toot).
Bundled dependencies retain their own licenses and metadata.
