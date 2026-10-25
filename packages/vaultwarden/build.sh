TERMUX_PKG_HOMEPAGE=https://github.com/dani-garcia/vaultwarden
TERMUX_PKG_DESCRIPTION="Unofficial Bitwarden-compatible API server (SQLite, no web vault)"
TERMUX_PKG_LICENSE="AGPL-3.0"
TERMUX_PKG_LICENSE_FILE="LICENSE.txt"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="1.37.4"
TERMUX_PKG_SRCURL="https://codeload.github.com/dani-garcia/vaultwarden/tar.gz/refs/tags/${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=d31a3ef5456619cfe424f0586f4ecadd186e22513a93bbeab6bc2f09cda803a7
TERMUX_PKG_DEPENDS="ca-certificates, libsqlite, openssl"
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"

termux_step_pre_configure() {
    TERMUX_RUST_VERSION=1.99.0
    termux_setup_rust
    export CFLAGS_aarch64_linux_android="$CFLAGS"
    unset CFLAGS
    export PKG_CONFIG_ALLOW_CROSS=1
    export OPENSSL_NO_VENDOR=1
    export OPENSSL_DIR="$TERMUX_PREFIX"
    export OPENSSL_LIB_DIR="$TERMUX_PREFIX/lib"
    export OPENSSL_INCLUDE_DIR="$TERMUX_PREFIX/include"
    export LIBSQLITE3_SYS_USE_PKG_CONFIG=1
    export VW_VERSION="$TERMUX_PKG_VERSION"
}

termux_step_configure() { :; }

termux_step_make() {
    cargo build --locked --jobs "$TERMUX_PKG_MAKE_PROCESSES" --target "$CARGO_TARGET_NAME" \
        --profile release-low --no-default-features --features sqlite_system
}

termux_step_make_install() {
    install -Dm700 "target/$CARGO_TARGET_NAME/release-low/vaultwarden" "$TERMUX_PREFIX/libexec/vaultwarden"
    install -Dm700 "$TERMUX_PKG_BUILDER_DIR/vaultwarden" "$TERMUX_PREFIX/bin/vaultwarden"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/vaultwarden/README.md"
    install -Dm600 .env.template "$TERMUX_PREFIX/share/doc/vaultwarden/upstream.env.example"
    install -Dm600 Cargo.lock "$TERMUX_PREFIX/share/doc/vaultwarden/Cargo.lock"
    cargo metadata --locked --format-version 1 --filter-platform "$CARGO_TARGET_NAME" \
        --no-default-features --features sqlite_system > "$TERMUX_PKG_TMPDIR/dependencies.json"
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-licenses.py" cargo "$TERMUX_PKG_TMPDIR/dependencies.json" \
        "$TERMUX_PREFIX/share/doc/vaultwarden/dependency-licenses"

    # Ship AGPL corresponding source with the signed release, including the
    # locked, statically linked Rust dependencies and this package's build files.
    local source="$TERMUX_PKG_TMPDIR/vaultwarden-${TERMUX_PKG_VERSION}-source"
    mkdir -p "$source/.cargo" "$source/termux-packaging" "$TERMUX_SCRIPTDIR/output/sources"
    tar --exclude=./target --exclude=./.git -cf - . | tar -xf - -C "$source"
    cargo vendor --locked "$source/vendor" > "$source/.cargo/config.toml"
    # cargo vendor emits an absolute path when given one; make the archive usable elsewhere.
    sed -i "s|directory = \"$source/vendor\"|directory = \"vendor\"|" "$source/.cargo/config.toml"
    cp "$TERMUX_PKG_BUILDER_DIR/build.sh" "$TERMUX_PKG_BUILDER_DIR/vaultwarden" \
        "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PKG_BUILDER_DIR/"*.py \
        "$TERMUX_PKG_BUILDER_DIR/"*.patch "$source/termux-packaging/"
    cp -R "$TERMUX_PKG_BUILDER_DIR/license-texts" "$source/termux-packaging/"
    tar -czf "$TERMUX_SCRIPTDIR/output/sources/vaultwarden-${TERMUX_PKG_VERSION}-${TERMUX_PKG_REVISION:-0}-source.tar.gz" \
        -C "$TERMUX_PKG_TMPDIR" "$(basename "$source")"
}
