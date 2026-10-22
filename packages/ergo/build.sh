TERMUX_PKG_HOMEPAGE=https://github.com/ergochat/ergo
TERMUX_PKG_DESCRIPTION="Modern IRC server with integrated bouncer features"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="2.19.1"
TERMUX_PKG_SRCURL="https://codeload.github.com/ergochat/ergo/tar.gz/refs/tags/v${TERMUX_PKG_VERSION}"
TERMUX_PKG_SHA256=7b1f6fac874a75c766ccd41d068f4408ac09aa30e594233afe87e7793d93c587
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_pre_configure() { termux_setup_golang; }
termux_step_configure() { :; }
termux_step_make() {
    CGO_ENABLED=1 go build -trimpath -tags "i18n mysql postgresql" -mod=vendor -ldflags "-s -w -X main.version=v2.19.1" -o ergo .
}
termux_step_make_install() {
    install -Dm700 ergo "$TERMUX_PREFIX/bin/ergo"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/ergo/README.md"
    install -Dm600 default.yaml "$TERMUX_PREFIX/share/doc/ergo/default.yaml"
    cp -r languages "$TERMUX_PREFIX/share/doc/ergo/"
}
