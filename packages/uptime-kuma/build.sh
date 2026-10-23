TERMUX_PKG_HOMEPAGE=https://github.com/louislam/uptime-kuma
TERMUX_PKG_DESCRIPTION="Self-hosted monitoring dashboard (experimental Android port)"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="2.5.7"
TERMUX_PKG_SRCURL="https://codeload.github.com/louislam/uptime-kuma/tar.gz/refs/tags/${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=501371f8f3a39bced0a8063119ec5a4d9afacf46a338f61cab66a518798de8ae
TERMUX_PKG_DEPENDS="nodejs-lts, libsqlite, libc++, ca-certificates"
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"

termux_step_pre_configure() {
    termux_setup_nodejs
    export npm_config_cache="$TERMUX_PKG_CACHEDIR/npm"
}
termux_step_configure() { :; }
termux_step_make() {
    # npm checks every downloaded tarball against upstream package-lock.json.
    # Lifecycle scripts are disabled: no downloaded native prebuilds execute.
    npm ci --ignore-scripts --no-audit --no-fund
    npm run build
    test -s dist/index.html
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-licenses.py" . "$TERMUX_PKG_TMPDIR/notices"
    npm prune --omit=dev --ignore-scripts --no-audit --no-fund
    # Remove upstream platform binaries (e.g. optional Oracle thick mode).
    # SSH uses its JS fallback; the only installed addon is built below.
    python3 "$TERMUX_PKG_BUILDER_DIR/remove-prebuilds.py" node_modules
    local sqlite=node_modules/@louislam/sqlite3
    local addon="$sqlite/lib/binding/napi-v6-android-arm64/node_sqlite3.node"
    mkdir -p "$(dirname "$addon")"
    # N-API 6 is stable across Node releases. These are the exact four sources
    # in upstream binding.gyp; reuse official Node headers and shared SQLite.
    "$CXX" $CPPFLAGS $CXXFLAGS -std=c++17 -fPIC -shared \
        -DNAPI_VERSION=6 -DNAPI_DISABLE_CPP_EXCEPTIONS=1 \
        -I"$TERMUX_PREFIX/include/node" -Inode_modules/node-addon-api \
        "$sqlite/src/backup.cc" "$sqlite/src/database.cc" \
        "$sqlite/src/node_sqlite3.cc" "$sqlite/src/statement.cc" \
        $LDFLAGS -lsqlite3 -o "$addon"
}
termux_step_make_install() {
    local private="$TERMUX_PREFIX/lib/uptime-kuma"
    local doc="$TERMUX_PREFIX/share/doc/uptime-kuma"
    mkdir -p "$private" "$doc"
    cp -a server src db extra dist node_modules package.json package-lock.json "$private/"
    cp -a "$TERMUX_PKG_TMPDIR/notices" "$doc/dependency-licenses"
    install -Dm600 package-lock.json "$doc/package-lock.json"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$doc/README.md"
    sed "s|@TERMUX_PREFIX@|$TERMUX_PREFIX|g" "$TERMUX_PKG_BUILDER_DIR/uptime-kuma" > "$TERMUX_PREFIX/bin/uptime-kuma"
    chmod 700 "$TERMUX_PREFIX/bin/uptime-kuma"
}
