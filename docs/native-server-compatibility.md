# Server compatibility evidence

The native tests use aarch64 Termux Bionic userspace in the pinned Termux-Pacman
container on an ARM64 Linux runner. They do not establish behavior on every
physical Android kernel, device memory limit, 16 KB page configuration or mod.
All test listeners bind to loopback. No package install starts a public listener.

| Server | Observed result | Remaining limits |
| --- | --- | --- |
| Official Terraria 1.4.5.8 | Native Mono world creation, valid protocol handshake/world info, save and reload | Real player sessions and physical devices untested |
| Pumpkin 0.2.0 (Java 26.3) | Native Android payload; protocol 777 status, clean stop, saved `level.dat` and unchanged world seed after restart | Gameplay, chunks, clients and mods untested |
| tModLoader 2026.08.3.0 (Terraria 1.4.4.9) | Native .NET/Mono world creation, wrong-version protocol rejection, save/reload and exit pass; package preflight still being completed | Real player sessions, arbitrary mods and Steam/Workshop untested; not yet active |
| TShock 6.2.1 (Terraria 1.4.5.8) | Startup and world creation work; valid protocol handling still fails loading Steamworks.NET type metadata | Inactive; no successful protocol/lifecycle claim |
| Valheim | Anonymous on-phone downloader and glibc/Box64 launch reach Unity/world creation | Inactive; steamclient aborts before game-server connection |

Evidence: [native server probes](https://github.com/josephluopooh/termux_repo/actions/runs/39832702343),
[packaged tModLoader preflight](https://github.com/josephluopooh/termux_repo/actions/runs/39830760816),
and [publication runtime tests](https://github.com/josephluopooh/termux_repo/actions/runs/39830760477).
The latter passed the four selected application tests preceding presenterm;
presenterm exposed a missing terminal capability response in the PTY harness.
These runs did not publish a release. A publication requires every runtime gate.

## Valheim runtime restriction

The tested Steamworks server depot is `1006`, manifest `4559160656493359681`.
Its `steamclient.so` SHA256 is
`1a99f39637a505ce2dbfec697dafa118c2d1b8df7dea1412557e2d5ad0a2c7d4`.
Disassembly places the first deliberate null store at offset `0x1e580d3`, after
`get_robust_list` reports no initialized pthread robust-futex list. The error
string is `futex robust_list not initialized by pthreads`.

The official glibc package's [syscall mapping](https://github.com/termux/glibc-packages/blob/75fa9e0c051e82221e0b957ac1967a215f6b5080/gpkg/glibc/fakesyscall.json)
returns `ENOSYS` for robust-list get/set, and its
[NPTL patch](https://github.com/termux/glibc-packages/blob/75fa9e0c051e82221e0b957ac1967a215f6b5080/gpkg/glibc/set-nptl-syscalls.patch)
removes registration. A correct solution needs thread-lifetime and mutex
owner-death semantics; a dummy pointer or skipped assertion is not a working
compatibility layer. The secondary Mono crash and separate certificate warning
are not established causes of this first failure. TLS verification remains on.
Android security settings are not altered.
