TERMUX_PKG_HOMEPAGE=https://github.com/Pryaxis/TShock
TERMUX_PKG_DESCRIPTION="TShock server downloader and native Termux Mono launcher"
TERMUX_PKG_LICENSE="Apache-2.0"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="6.2.1"
TERMUX_PKG_DEPENDS="python, ca-certificates, terraria-managed-support, dotnet-runtime-9.0, libsqlite"
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_SKIP_SRC_EXTRACT=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_configure() { :; }
termux_step_make() { :; }
termux_step_make_install() {
    install -Dm700 "$TERMUX_PKG_BUILDER_DIR/tshock-server" "$TERMUX_PREFIX/bin/tshock-server"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/tshock-server/README.md"
}
