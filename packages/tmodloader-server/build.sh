TERMUX_PKG_HOMEPAGE=https://github.com/tModLoader/tModLoader
TERMUX_PKG_DESCRIPTION="tModLoader server downloader and native Termux Mono launcher"
TERMUX_PKG_LICENSE="Apache-2.0"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="2026.08.3.0"
TERMUX_PKG_DEPENDS="python, ca-certificates, terraria-managed-support, dotnet-runtime-8.0, sdl2"
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_SKIP_SRC_EXTRACT=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_configure() { :; }
termux_step_make() { :; }
termux_step_make_install() {
    install -Dm700 "$TERMUX_PKG_BUILDER_DIR/tmodloader-server" "$TERMUX_PREFIX/bin/tmodloader-server"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/tmodloader-server/README.md"
}
