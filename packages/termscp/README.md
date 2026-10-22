# termscp 1.2.1

SFTP/SCP/FTP and remote file management. SMB and desktop keyring are disabled. Update through Pacman; the upstream self-updater is disabled.

Native Android/Bionic aarch64 build from the pinned upstream source, with its
Cargo.lock enforced. Install after following the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/termscp
termscp
```

Upstream: https://github.com/veeso/termscp/tree/v1.2.1

License: MIT; the package retains the upstream license. Dependencies retain
their own licenses. See the release build evidence for ELF checks and native
Termux container test output. A container smoke test is not a physical-device
or full end-to-end interoperability test.
