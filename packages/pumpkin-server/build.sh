TERMUX_PKG_HOMEPAGE=https://pumpkinmc.org/
TERMUX_PKG_DESCRIPTION="Pumpkin Minecraft server (upstream Android aarch64 build)"
TERMUX_PKG_LICENSE="GPL-3.0"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.2.0"
TERMUX_PKG_SRCURL="https://codeload.github.com/Pumpkin-MC/Pumpkin/tar.gz/refs/tags/0.2.0+26.3-26.51"
TERMUX_PKG_SHA256=a9634c6e1a3323824559f42a95a754b8ec4f9afc973501cc3830974c57835ea7
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"
TERMUX_PKG_DEPENDS="libc++"
TERMUX_PKG_BUILD_IN_SRC=true

termux_step_configure() { :; }
termux_step_make() { :; }
termux_step_make_install() {
    termux_download         "https://github.com/Pumpkin-MC/Pumpkin/releases/download/0.2.0%2B26.3-26.51/pumpkin-aarch64-android"         "$TERMUX_PKG_TMPDIR/pumpkin"         95d24e2f79376574f737419cfe60ec8c73712e7bcc69eefb8a4cb6ef4e9c9e2a
    install -Dm700 "$TERMUX_PKG_TMPDIR/pumpkin" "$TERMUX_PREFIX/bin/pumpkin"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/pumpkin-server/README.md"
    # The release distributes the matching source alongside the binary packages.
    # Preserve all locked dependency sources and their notices for GPL source access;
    # these are source-release assets, not additional Pacman dependency packages.
    termux_setup_rust
    RUSTUP_TOOLCHAIN="$TERMUX_RUST_VERSION" cargo vendor --locked --versioned-dirs vendor > cargo-vendor-config.toml
    mkdir -p .cargo
    cat cargo-vendor-config.toml >> .cargo/config.toml
    mkdir -p "$TERMUX_SCRIPTDIR/output/sources"
    tar -czf "$TERMUX_SCRIPTDIR/output/sources/pumpkin-0.2.0-source.tar.gz" -C "$TERMUX_PKG_SRCDIR" .
}
