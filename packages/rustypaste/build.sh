TERMUX_PKG_HOMEPAGE=https://github.com/orhun/rustypaste
TERMUX_PKG_DESCRIPTION="Minimal self-hosted file upload and pastebin service"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.18.1"
TERMUX_PKG_SRCURL="https://codeload.github.com/orhun/rustypaste/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=4b63be093e080d4a39e9ca03b378df96f0ae604e469a9c4d9bb437f9643524f0
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_pre_configure() {
    termux_setup_rust
    # Keep host build scripts separate from target compiler flags.
    unset CFLAGS
}

termux_step_configure() { :; }

termux_step_make() {
    cargo build --locked --jobs "$TERMUX_PKG_MAKE_PROCESSES" --target "$CARGO_TARGET_NAME" --release 
}

termux_step_make_install() {
    install -Dm700 "target/$CARGO_TARGET_NAME/release/rustypaste" "$TERMUX_PREFIX/bin/rustypaste"
    install -Dm600 config.toml "$TERMUX_PREFIX/share/doc/rustypaste/config.toml"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/rustypaste/README.md"
}
