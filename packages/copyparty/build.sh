TERMUX_PKG_HOMEPAGE=https://github.com/9001/copyparty
TERMUX_PKG_DESCRIPTION="Portable HTTP file server with resumable uploads and WebDAV"
TERMUX_PKG_LICENSE="MIT, BSD 3-Clause, BSD 2-Clause, Apache-2.0, OFL-1.1"
TERMUX_PKG_LICENSE_FILE="LICENSE, LICENSE.txt, copyparty/res/COPYING.txt"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="1.20.26"
TERMUX_PKG_SRCURL=("https://github.com/9001/copyparty/releases/download/v${TERMUX_PKG_VERSION}/copyparty-${TERMUX_PKG_VERSION}.tar.gz"
    "https://files.pythonhosted.org/packages/df/bf/f7da0350254c0ed7c72f3e33cef02e048281fec7ecec5f032d4aac52226b/jinja2-3.1.6.tar.gz"
    "https://files.pythonhosted.org/packages/7e/99/7690b6d4034fffd95959cbe0c02de8deb3098cc577c67bb6a24fe5d7caa7/markupsafe-3.0.3.tar.gz")
TERMUX_PKG_SHA256=(ac7ea05bde8d431b32cc2ff618f2754e46bd967bf10deaa6654dac9a449a6ff9
    0137fb05990d35f1275a587e9aee6d56da821fc83491a0fb838183be43f66d6d
    722695808f4b6457b320fdc131280796bdceb04ab50fe1795cd540799ebe1698)
TERMUX_PKG_DEPENDS="python (>= 3.9)"
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_configure() { :; }
termux_step_make() { :; }
termux_step_make_install() {
    local private="$TERMUX_PREFIX/lib/copyparty"
    local doc="$TERMUX_PREFIX/share/doc/copyparty"
    mkdir -p "$private" "$doc/dependency-licenses"
    # Jinja2/MarkupSafe have no official recipes in the pinned Termux tree.
    # Keep only these mandatory Python dependencies private to this package.
    cp -aL copyparty "$private/"
    cp -a jinja2-3.1.6/src/jinja2 markupsafe-3.0.3/src/markupsafe "$private/"
    # The Python fallback avoids a Python-minor-version-specific extension.
    find "$private" -type f \( -name '*.c' -o -name '*.pyc' \) -delete
    install -Dm600 jinja2-3.1.6/LICENSE.txt "$doc/dependency-licenses/Jinja2-LICENSE.txt"
    install -Dm600 markupsafe-3.0.3/LICENSE.txt "$doc/dependency-licenses/MarkupSafe-LICENSE.txt"
    install -Dm600 copyparty/res/COPYING.txt "$doc/dependency-licenses/copyparty-COPYING.txt"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$doc/README.md"
    install -Dm600 "$TERMUX_PKG_BUILDER_DIR/dependencies.json" "$doc/dependencies.json"
    sed "s|@TERMUX_PREFIX@|$TERMUX_PREFIX|g" "$TERMUX_PKG_BUILDER_DIR/copyparty" > "$TERMUX_PREFIX/bin/copyparty"
    chmod 700 "$TERMUX_PREFIX/bin/copyparty"
}
