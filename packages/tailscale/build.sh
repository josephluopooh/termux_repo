TERMUX_PKG_HOMEPAGE=https://tailscale.com
TERMUX_PKG_DESCRIPTION="Native Tailscale CLI and userspace networking daemon"
TERMUX_PKG_LICENSE="BSD 3-Clause"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="1.104.2"
TERMUX_PKG_SRCURL="https://codeload.github.com/tailscale/tailscale/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=4c1c806e16507414a1459afcdc399f6a1323c21a1ac90f07bea0465fd8fd7e1d
TERMUX_PKG_DEPENDS="ca-certificates"
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"

termux_step_pre_configure() {
    # This release requires Go 1.27.3. Reuse the pinned framework helper and
    # its Android runtime patches with only the compiler version/hash updated.
    # GOTOOLCHAIN=local prevents Go silently switching to an unpatched compiler.
    python3 - "$TERMUX_SCRIPTDIR/scripts/build/setup/termux_setup_golang.sh" "$TERMUX_PKG_TMPDIR/setup-golang.sh" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1]).read_text()
for old, new in [
    ('go1.27.2', 'go1.27.3'),
    ('ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5',
     '65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40'),
]:
    assert source.count(old) == 1, 'Review Go helper after upstream pin change'
    source = source.replace(old, new)
Path(sys.argv[2]).write_text(source)
PY
    . "$TERMUX_PKG_TMPDIR/setup-golang.sh"
    termux_setup_golang
    export CGO_ENABLED=1 GOTOOLCHAIN=local
}

termux_step_configure() { :; }

termux_step_make() {
    # GOOS=android and GOARCH=arm64 come from the Termux framework; CGO uses
    # its Android NDK/Bionic compiler. Keep upstream androidbin/androiddns.
    test "$GOOS" = android && test "$GOARCH" = arm64
    # Upstream SSH excludes Android; a desktop system tray is unavailable.
    go build -trimpath -buildvcs=false -mod=readonly -tags ts_omit_ssh,ts_omit_systray \
        -ldflags "-s -w -X tailscale.com/version.longStamp=${TERMUX_PKG_VERSION} -X tailscale.com/version.shortStamp=${TERMUX_PKG_VERSION}" \
        -o "$TERMUX_PKG_TMPDIR/bin/" ./cmd/tailscale ./cmd/tailscaled
}

termux_step_make_install() {
    install -Dm700 "$TERMUX_PKG_TMPDIR/bin/tailscale" "$TERMUX_PREFIX/bin/tailscale"
    install -Dm700 "$TERMUX_PKG_TMPDIR/bin/tailscaled" "$TERMUX_PREFIX/libexec/tailscaled"
    install -Dm700 "$TERMUX_PKG_BUILDER_DIR/tailscaled" "$TERMUX_PREFIX/bin/tailscaled"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/tailscale/README.md"
    install -Dm600 go.mod "$TERMUX_PREFIX/share/doc/tailscale/go.mod"
    install -Dm600 go.sum "$TERMUX_PREFIX/share/doc/tailscale/go.sum"
    go list -buildvcs=false -tags ts_omit_ssh,ts_omit_systray -deps -json ./cmd/tailscale ./cmd/tailscaled > "$TERMUX_PKG_TMPDIR/dependencies.json"
    python3 "$TERMUX_PKG_BUILDER_DIR/collect-licenses.py" go "$TERMUX_PKG_TMPDIR/dependencies.json" "$TERMUX_PREFIX/share/doc/tailscale/dependency-licenses"
    install -Dm600 "$GOROOT/LICENSE" "$TERMUX_PREFIX/share/doc/tailscale/dependency-licenses/Go-LICENSE"
}
