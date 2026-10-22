# Package selection and dependency policy

These **unselected candidates** are preserved under `candidates/`, outside the
active package manifest, while the owner chooses from a broader shortlist.
No candidate is authorized for publication yet.

The October 2026 candidate investigation focuses on networking, IRC, self-hosting, Rust
development, terminal productivity and game servers. Candidates were checked
with Repology, then cross-checked against the **actual official Termux** main,
root and X11 package names and `Provides` aliases. A Repology record alone does
not establish a Termux gap.

The official source-tree check used
`termux/termux-packages@facb27bc85ef36fd1120d4ae990fbd59e134fc61`, alongside
the live aarch64 main/root/X11 indexes. Builds separately use this repository's
pinned Termux-Pacman checkout from `sources.json`, and the runtime job resolves
dependencies from its official signed Pacman repositories.

| Addition | Repology project | Reason / intentional feature choice |
| --- | --- | --- |
| rainfrog 0.4.6 | [rainfrog](https://repology.org/project/rainfrog/versions) | Database TUI; upstream Termux `--no-default-features` |
| chisel 1.12.0 | [chisel-tcp-tunnel-over-http](https://repology.org/project/chisel-tcp-tunnel-over-http/versions) | Stable authenticated tunnels; 1.13.0 is prerelease |
| rustypaste 0.18.1 | [rustypaste](https://repology.org/project/rustypaste/versions) | Small self-hosted paste service |
| presenterm 0.16.1 | [presenterm](https://repology.org/project/presenterm/versions) | Markdown slides without a desktop |
| Ergo 2.19.1 | [ergo-irc-server](https://repology.org/project/ergo-irc-server/versions) | IRC server; also checked aliases `oragono` and `ergochat` |
| termscp 1.2.1 | [termscp](https://repology.org/project/termscp/versions) | File transfer UI; no SMB/desktop keyring; Pacman owns updates |
| rathole 0.5.0 | [rathole](https://repology.org/project/rathole/versions) | Stable compact reverse tunnel; upstream embedded/Noise feature set |
| lazyjj 0.6.1 | [lazyjj](https://repology.org/project/lazyjj/versions) | UI for official Jujutsu; TUR is distinct from official Termux |

Already-official candidates deliberately excluded: gping, soju, senpai, catgirl,
gurk, oha, xh, miniserve and jujutsu. Posting was replaced by lazyjj to avoid
introducing a large private Python/native-extension dependency tree. mcabber was
not selected because it adds the absent Loudmouth dependency and has an old
stable release.

## Reuse official dependencies

The repository publishes only the selected applications and the pre-existing
cJSON/WeeChat/toot packages. Native Mono and its framework libraries, Python,
OpenSSL, zlib, libc++, Jujutsu and other runtime libraries resolve through
official Termux-Pacman packages. Build-only fallback dependencies are recorded
as evidence but are **not** copied into the published package index.

Rust and Go applications compile their normal source dependencies using the
upstream lockfiles/checksums. Those language crates/modules are not separate
Pacman packages. This is different from mirroring every system dependency.
The existing toot private Python dependency layout is unchanged by this work.

## Servers still under native compatibility investigation

The selected server recipes are vanilla Terraria (native Mono, explicit official
download) and Pumpkin (upstream Android binary). TShock 6.2.1 and tModLoader
2026.08.3.0 are being tested separately with native Termux .NET 9/8. Their Linux
ARM64 apphosts are not Android binaries. MonoMod native detours, Android platform
detection and native-library ABI are separate requirements from managed assembly
compatibility. The probe workflow uploads logs only, not proprietary server
payloads. There are no proot packages or fallback launchers.

Valheim is a separate native Unity/Linux server, not a Mono-only Terraria-style
managed server. Its glibc/architecture requirements and possible CPU translation
route need separate validation before any package can be advertised.
