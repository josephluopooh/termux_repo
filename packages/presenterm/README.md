# presenterm 0.16.1

Useful for terminal presentations and technical notes. Image display depends on the terminal graphics protocol; ordinary Termux does not gain Kitty graphics from this package.

Native Android/Bionic aarch64 build from the pinned upstream source, with its
Cargo.lock enforced. Install after following the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/presenterm
presenterm slides.md
```

Upstream: https://github.com/mfontanini/presenterm/tree/v0.16.1

The recipe links to official `oniguruma` rather than building its bundled C
copy. It preserves the upstream Cargo.lock. Text slides are the supported
baseline; use `presenterm --image-protocol ascii-blocks slides.md` if the
terminal has no graphics protocol. PDF export and external renderers are not
installed or promised by this package.

License: BSD-2-Clause. The package stages dependency notices and Cargo.lock
under `$PREFIX/share/doc/presenterm`. TUR tree
`129d9f5e06a37f19313833b640d7bf0f7eb781f5` had no presenterm recipe. This
continues the repository's existing candidate draft.

`python packages/presenterm/smoke-test.py` renders a generated text slide in a
pseudo-terminal and checks its content. The release workflow requires this
test after a native Pacman installation. A container test is not a physical
phone or graphics-protocol compatibility test.
