TERMUX_PKG_HOMEPAGE=https://github.com/jpillora/chisel
TERMUX_PKG_DESCRIPTION="TCP and UDP tunnels over HTTP"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="1.12.0"
TERMUX_PKG_SRCURL="https://codeload.github.com/jpillora/chisel/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=5c25f054b64814f770725593db525faa1999960aecf4eb15c86529dea573c431
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"
TERMUX_PKG_DEPENDS="ca-certificates"

termux_step_pre_configure() {
    termux_setup_golang
    export CGO_ENABLED=1
}
termux_step_configure() { :; }
termux_step_make() {
    go build -trimpath -mod=readonly -ldflags "-s -w -X github.com/jpillora/chisel/share.BuildVersion=${TERMUX_PKG_VERSION}" -o chisel .
}
termux_step_make_install() {
    go list -deps -json . > "$TERMUX_PKG_TMPDIR/dependencies.json"
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-licenses.py" go "$TERMUX_PKG_TMPDIR/dependencies.json" "$TERMUX_PREFIX/share/doc/chisel/dependency-licenses"
    install -Dm600 "$GOROOT/LICENSE" "$TERMUX_PREFIX/share/doc/chisel/dependency-licenses/Go-LICENSE"
    install -Dm600 go.mod "$TERMUX_PREFIX/share/doc/chisel/go.mod"
    install -Dm600 go.sum "$TERMUX_PREFIX/share/doc/chisel/go.sum"
    install -Dm700 chisel "$TERMUX_PREFIX/bin/chisel"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/chisel/README.md"
}
