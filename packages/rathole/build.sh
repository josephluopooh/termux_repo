TERMUX_PKG_HOMEPAGE=https://github.com/rathole-org/rathole
TERMUX_PKG_DESCRIPTION="Reverse proxy for NAT traversal"
TERMUX_PKG_LICENSE="Apache-2.0"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.5.0"
TERMUX_PKG_SRCURL="https://codeload.github.com/rathole-org/rathole/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=c8698dc507c4c2f7e0032be24cac42dd6656ac1c52269875d17957001aa2de41
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_pre_configure() {
    termux_setup_rust
    # Keep host build scripts separate from target compiler flags.
    unset CFLAGS
}

termux_step_configure() { :; }

termux_step_make() {
    cargo build --locked --jobs "$TERMUX_PKG_MAKE_PROCESSES" --target "$CARGO_TARGET_NAME" --release --no-default-features --features embedded
}

termux_step_make_install() {
    install -Dm700 "target/$CARGO_TARGET_NAME/release/rathole" "$TERMUX_PREFIX/bin/rathole"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/rathole/README.md"
}
