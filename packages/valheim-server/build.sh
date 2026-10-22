TERMUX_PKG_HOMEPAGE=https://www.valheimgame.com/
TERMUX_PKG_DESCRIPTION="Experimental Valheim downloader and no-proot Box64 launcher"
TERMUX_PKG_LICENSE="Apache-2.0"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.1.0"
TERMUX_PKG_DEPENDS="python, ca-certificates, dotnet-runtime-9.0"
# These are runtime-only packages from the separate signed Pacman [gpkg] repo.
# The Bionic builder cannot resolve their recipes. The launcher requires them
# before setup/start; see README for the explicit full-upgrade transaction.
TERMUX_PKG_SUGGESTS="box64-glibc, glibc, gcc-libs-glibc, libpulse-glibc, libogg-glibc"
TERMUX_PKG_EXCLUDED_ARCHES="arm, i686, x86_64"
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_SKIP_SRC_EXTRACT=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_configure() { :; }
termux_step_make() { :; }
termux_step_make_install() {
    install -Dm755 "$TERMUX_PKG_BUILDER_DIR/valheim-server" "$TERMUX_PREFIX/bin/valheim-server"
    install -Dm644 "$TERMUX_PKG_BUILDER_DIR/README.md" "$TERMUX_PREFIX/share/doc/valheim-server/README.md"
}
