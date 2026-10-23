TERMUX_PKG_HOMEPAGE=https://github.com/AdguardTeam/AdGuardHome
TERMUX_PKG_DESCRIPTION="Rootless DNS filtering server and dashboard (experimental Android port)"
TERMUX_PKG_LICENSE="GPL-3.0"
TERMUX_PKG_LICENSE_FILE="LICENSE.txt"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.107.79"
TERMUX_PKG_SRCURL="https://codeload.github.com/AdguardTeam/AdGuardHome/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=5f4fa119f24ea741bb8cecfa74203165fe6b86b904cef05ff429fb227b07d425
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"
TERMUX_PKG_DEPENDS="ca-certificates"

termux_step_pre_configure() {
    termux_setup_golang
    termux_setup_nodejs
    export CGO_ENABLED=1
    export GOTELEMETRY=off
    export npm_config_cache="$TERMUX_PKG_CACHEDIR/npm"
    # Stable releases embed client/, not the next-API client_v2/ tree.
    npm ci --prefix client --ignore-scripts --no-audit --no-fund
    npm run --prefix client build-prod
}
termux_step_configure() { :; }
termux_step_make() {
    go build -trimpath -mod=readonly -ldflags "-s -w -X github.com/AdguardTeam/AdGuardHome/internal/version.version=v${TERMUX_PKG_VERSION} -X github.com/AdguardTeam/AdGuardHome/internal/version.channel=release -X github.com/AdguardTeam/AdGuardHome/internal/version.committime=${SOURCE_DATE_EPOCH:-unknown}" -o AdGuardHome .
}
termux_step_make_install() {
    local docs="$TERMUX_PREFIX/share/doc/adguardhome"
    install -Dm700 AdGuardHome "$TERMUX_PREFIX/libexec/adguardhome/AdGuardHome"
    install -Dm700 "$TERMUX_PKG_BUILDER_DIR/adguardhome" "$TERMUX_PREFIX/bin/adguardhome"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/AdGuardHome.yaml" "$TERMUX_PREFIX/share/adguardhome/AdGuardHome.yaml"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$docs/README.md"
    install -Dm600 go.mod "$docs/go.mod"
    install -Dm600 go.sum "$docs/go.sum"
    install -Dm600 client/package-lock.json "$docs/client-package-lock.json"
    go list -deps -json . > "$TERMUX_PKG_TMPDIR/dependencies.json"
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-licenses.py" go "$TERMUX_PKG_TMPDIR/dependencies.json" "$docs/dependency-licenses"
    install -Dm600 "$GOROOT/LICENSE" "$docs/dependency-licenses/Go-LICENSE"
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-client-licenses.py" client "$docs/client-licenses"
    # Preserve patched source and dependency sources for the GPL binary/UI.
    python3 "$TERMUX_PKG_BUILDER_DIR/source-archive.py" \
        "$TERMUX_PKG_SRCDIR" "$TERMUX_PKG_BUILDER_DIR" \
        "$TERMUX_PKG_TMPDIR/dependencies.json" "$(go env GOMODCACHE)" \
        "$TERMUX_OUTPUT_DIR/sources/adguardhome-${TERMUX_PKG_VERSION}-source.tar.gz"
}
