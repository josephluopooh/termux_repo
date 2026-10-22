TERMUX_PKG_HOMEPAGE=https://ntfy.sh
TERMUX_PKG_DESCRIPTION="HTTP notification client and self-hosted API server"
TERMUX_PKG_LICENSE="Apache-2.0"
TERMUX_PKG_LICENSE_FILE="LICENSE, LICENSE.GPLv2"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="2.32.0"
TERMUX_PKG_SRCURL="https://codeload.github.com/binwiederhier/ntfy/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=afa46845907dc9eef6f20e25a8ec65309377aa7f754610fc0f23798f45cc0a97
TERMUX_PKG_DEPENDS="ca-certificates, libsqlite"
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"
TERMUX_PKG_CONFFILES="etc/ntfy/server.yml"
TERMUX_PKG_AUTO_UPDATE=false

termux_step_pre_configure() {
    termux_setup_golang
    export CGO_ENABLED=1
    # Use upstream's CLI/API-only build convention; do not ship a blank web UI.
    mkdir -p server/docs server/site
    printf '%s\n' 'Web UI not included in this CLI/API package.' > server/site/app.html
    printf '%s\n' 'Documentation: https://ntfy.sh/docs/' > server/docs/index.html
}

termux_step_configure() { :; }
termux_step_make() {
    go build -trimpath -mod=readonly -tags "libsqlite3,sqlite_omit_load_extension,osusergo,netgo" \
        -ldflags "-s -w -X main.version=${TERMUX_PKG_VERSION} -X main.commit=v${TERMUX_PKG_VERSION} -X main.date=${SOURCE_DATE_EPOCH:-unknown}" \
        -o ntfy .
}

termux_step_make_install() {
    install -Dm700 ntfy "$TERMUX_PREFIX/bin/ntfy"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/server.yml" "$TERMUX_PREFIX/etc/ntfy/server.yml"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/ntfy/README.md"
    install -Dm600 server/server.yml "$TERMUX_PREFIX/share/doc/ntfy/server.example.yml"
    install -Dm600 client/client.yml "$TERMUX_PREFIX/share/doc/ntfy/client.example.yml"
    install -Dm600 go.mod "$TERMUX_PREFIX/share/doc/ntfy/go.mod"
    install -Dm600 go.sum "$TERMUX_PREFIX/share/doc/ntfy/go.sum"
    go list -deps -json -tags "libsqlite3,sqlite_omit_load_extension,osusergo,netgo" . > "$TERMUX_PKG_TMPDIR/dependencies.json"
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-licenses.py" go "$TERMUX_PKG_TMPDIR/dependencies.json" "$TERMUX_PREFIX/share/doc/ntfy/dependency-licenses"
    install -Dm600 "$GOROOT/LICENSE" "$TERMUX_PREFIX/share/doc/ntfy/dependency-licenses/Go-LICENSE"
}
