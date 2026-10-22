# lazyjj 0.6.1

A terminal interface for Rust development repositories using official Termux Jujutsu. This package fills the UI gap; it does not duplicate the official jj package.

Native Android/Bionic aarch64 build from the pinned upstream source, with its
Cargo.lock enforced. Install after following the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/lazyjj
cd /path/to/jj/repository
lazyjj
```

Upstream: https://github.com/Cretezy/lazyjj/tree/v0.6.1

License: Apache-2.0; the package retains the upstream license. Dependencies retain
their own licenses. See the release build evidence for ELF checks and native
Termux container test output. A container smoke test is not a physical-device
or full end-to-end interoperability test.
