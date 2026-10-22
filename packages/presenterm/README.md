# presenterm 0.16.1

Useful for terminal presentations and technical notes. Image display depends on the terminal graphics protocol; ordinary Termux does not gain Kitty graphics from this package.

Native Android/Bionic aarch64 build from the pinned upstream source, with its
Cargo.lock enforced. Install after following the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/presenterm
presenterm slides.md
```

Upstream: https://github.com/mfontanini/presenterm/tree/v0.16.1

License: BSD-2-Clause; the package retains the upstream license. Dependencies retain
their own licenses. See the release build evidence for ELF checks and native
Termux container test output. A container smoke test is not a physical-device
or full end-to-end interoperability test.
