TERMUX_PKG_HOMEPAGE=https://github.com/mfontanini/presenterm
TERMUX_PKG_DESCRIPTION="Markdown slides in the terminal"
TERMUX_PKG_LICENSE="BSD 2-Clause"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.16.1"
TERMUX_PKG_SRCURL="https://codeload.github.com/mfontanini/presenterm/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=221258deae7204c65a55d3666aaea5fa157312b4196a59abc60ba4d363787c10
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"
TERMUX_PKG_DEPENDS="oniguruma"

termux_step_pre_configure() {
    termux_setup_rust
    # Preserve target flags without passing Android flags to host build scripts.
    export CFLAGS_aarch64_linux_android="$CFLAGS"
    unset CFLAGS
    export PKG_CONFIG_ALLOW_CROSS=1
    export RUSTONIG_SYSTEM_LIBONIG=1
}

termux_step_configure() { :; }

termux_step_make() {
    cargo build --locked --jobs "$TERMUX_PKG_MAKE_PROCESSES" --target "$CARGO_TARGET_NAME" --release
}

termux_step_make_install() {
    cargo metadata --locked --format-version 1 --filter-platform "$CARGO_TARGET_NAME" > "$TERMUX_PKG_TMPDIR/dependencies.json"
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-licenses.py" cargo "$TERMUX_PKG_TMPDIR/dependencies.json" "$TERMUX_PREFIX/share/doc/presenterm/dependency-licenses"
    install -Dm600 Cargo.lock "$TERMUX_PREFIX/share/doc/presenterm/Cargo.lock"
    install -Dm700 "target/$CARGO_TARGET_NAME/release/presenterm" "$TERMUX_PREFIX/bin/presenterm"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/presenterm/README.md"
}
