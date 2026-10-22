TERMUX_PKG_HOMEPAGE=https://pumpkinmc.org/
TERMUX_PKG_DESCRIPTION="Pumpkin native Android server downloader and launcher"
TERMUX_PKG_LICENSE="Apache-2.0"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.2.0"
TERMUX_PKG_AUTO_UPDATE=false
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_SKIP_SRC_EXTRACT=true
TERMUX_PKG_DEPENDS="python, ca-certificates, libc++"

termux_step_configure() { :; }
termux_step_make() { :; }
termux_step_make_install() {
    install -Dm700 "$TERMUX_PKG_BUILDER_DIR/pumpkin-server" "$TERMUX_PREFIX/bin/pumpkin-server"
    ln -s pumpkin-server "$TERMUX_PREFIX/bin/pumpkin"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/pumpkin-server/README.md"
}
