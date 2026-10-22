TERMUX_PKG_HOMEPAGE=https://terraria.org/
TERMUX_PKG_DESCRIPTION="Official vanilla Terraria server downloader and native Mono launcher"
TERMUX_PKG_LICENSE="Apache-2.0"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="1.4.5.8"
TERMUX_PKG_DEPENDS="python, ca-certificates, mono, mono-libs"
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_SKIP_SRC_EXTRACT=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_configure() { :; }
termux_step_make() { :; }
termux_step_make_install() {
    install -Dm700 "$TERMUX_PKG_BUILDER_DIR/terraria-server" "$TERMUX_PREFIX/bin/terraria-server"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/terraria-server/README.md"
}
