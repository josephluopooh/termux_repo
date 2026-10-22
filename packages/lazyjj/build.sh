TERMUX_PKG_HOMEPAGE=https://github.com/Cretezy/lazyjj
TERMUX_PKG_DESCRIPTION="Terminal UI for Jujutsu version control"
TERMUX_PKG_LICENSE="Apache-2.0"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.6.1"
TERMUX_PKG_SRCURL="https://codeload.github.com/Cretezy/lazyjj/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=34a702d55ec4c5d0ca016d4f71f4061ccca347ac88c80018229f6cf50141e208
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_DEPENDS="jujutsu"

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
    install -Dm700 "target/$CARGO_TARGET_NAME/release/lazyjj" "$TERMUX_PREFIX/bin/lazyjj"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/lazyjj/README.md"
}
