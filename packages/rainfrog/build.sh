TERMUX_PKG_HOMEPAGE=https://github.com/achristmascarl/rainfrog
TERMUX_PKG_DESCRIPTION="Database management TUI for SQLite, PostgreSQL and MySQL"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.4.6"
TERMUX_PKG_SRCURL="https://codeload.github.com/achristmascarl/rainfrog/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=30d4c4843c040441422eb9d64d386bf35f6c2c1de345944cc3e12f17e0cd0ca5
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"
TERMUX_PKG_DEPENDS="ca-certificates, libsqlite"

termux_step_pre_configure() {
    termux_setup_rust
    # Preserve target flags without passing Android flags to host build scripts.
    export CFLAGS_aarch64_linux_android="$CFLAGS"
    unset CFLAGS
    export PKG_CONFIG_ALLOW_CROSS=1
    export LIBSQLITE3_SYS_USE_PKG_CONFIG=1
}

termux_step_configure() { :; }

termux_step_make() {
    cargo build --locked --jobs "$TERMUX_PKG_MAKE_PROCESSES" --target "$CARGO_TARGET_NAME" --release --no-default-features
}

termux_step_make_install() {
    cargo metadata --locked --format-version 1 --filter-platform "$CARGO_TARGET_NAME" --no-default-features > "$TERMUX_PKG_TMPDIR/dependencies.json"
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-licenses.py" cargo "$TERMUX_PKG_TMPDIR/dependencies.json" "$TERMUX_PREFIX/share/doc/rainfrog/dependency-licenses"
    install -Dm600 Cargo.lock "$TERMUX_PREFIX/share/doc/rainfrog/Cargo.lock"
    install -Dm700 "target/$CARGO_TARGET_NAME/release/rainfrog" "$TERMUX_PREFIX/bin/rainfrog"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/rainfrog/README.md"
}
