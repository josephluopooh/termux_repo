TERMUX_PKG_HOMEPAGE=https://toot.bezdomni.net/
TERMUX_PKG_DESCRIPTION="Mastodon command-line client and terminal user interface"
TERMUX_PKG_LICENSE="GPL-3.0"
TERMUX_PKG_LICENSE_FILE="LICENSE"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="0.52.1"
TERMUX_PKG_SRCURL="https://files.pythonhosted.org/packages/source/t/toot/toot-${TERMUX_PKG_VERSION}.tar.gz"
TERMUX_PKG_SHA256=b737173be5587522077c18c4024eb1741a4a30e59d3165e72fd6ce4519d2fecb
TERMUX_PKG_DEPENDS="ca-certificates, python (>= 3.11.5)"
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_configure() { :; }
termux_step_make() { :; }

termux_step_make_install() {
	# The pinned upstream has no packages for these pure-Python dependencies.
	# Repack the upstream universal wheels, keeping their metadata and licenses
	# in a private directory owned entirely by Pacman. No runtime pip hooks.
	python3 -m pip --isolated --disable-pip-version-check install \
		--no-deps --no-compile --require-hashes --only-binary=:all: \
		--platform=any --target "$TERMUX_PREFIX/lib/toot" \
		-r "$TERMUX_PKG_BUILDER_DIR/requirements.txt"
	rm -rf "$TERMUX_PREFIX/lib/toot/bin"
	# Use the official Termux CA bundle and its normal security updates.
	ln -sf "$TERMUX_PREFIX/etc/tls/cert.pem" \
		"$TERMUX_PREFIX/lib/toot/certifi/cacert.pem"
	install -Dm600 "$TERMUX_PKG_BUILDER_DIR/requirements.txt" \
		"$TERMUX_PREFIX/share/doc/toot/requirements.txt"
	sed "s|@TERMUX_PREFIX@|$TERMUX_PREFIX|g" \
		"$TERMUX_PKG_BUILDER_DIR/toot" > "$TERMUX_PREFIX/bin/toot"
	chmod 700 "$TERMUX_PREFIX/bin/toot"
}
