TERMUX_PKG_HOMEPAGE=https://github.com/veeso/termscp
TERMUX_PKG_DESCRIPTION="Terminal file transfer client and explorer"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="1.2.1"
TERMUX_PKG_SRCURL="https://codeload.github.com/veeso/termscp/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=378b06607669edd6fdbcf1f3e040928b4a5e41c3792334d8b140270bd9afe0b7
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_DEPENDS="openssl, zlib"

termux_step_pre_configure() {
    termux_setup_rust
    # Keep host build scripts separate from target compiler flags.
    unset CFLAGS
    export OPENSSL_NO_VENDOR=1 OPENSSL_DIR="$TERMUX_PREFIX"
    python3 "$TERMUX_PKG_BUILDER_DIR/disable-updater.py"
}

termux_step_configure() { :; }

termux_step_make() {
    cargo build --locked --jobs "$TERMUX_PKG_MAKE_PROCESSES" --target "$CARGO_TARGET_NAME" --release --no-default-features
}

termux_step_make_install() {
    install -Dm700 "target/$CARGO_TARGET_NAME/release/termscp" "$TERMUX_PREFIX/bin/termscp"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/termscp/README.md"
}
