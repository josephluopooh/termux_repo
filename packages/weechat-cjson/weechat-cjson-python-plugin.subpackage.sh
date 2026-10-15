TERMUX_SUBPKG_INCLUDE="lib/weechat/plugins/python.so"
TERMUX_SUBPKG_DESCRIPTION="WeeChat Python3 Plugin"
TERMUX_SUBPKG_CONFLICTS="weechat-python-plugin"
TERMUX_SUBPKG_PROVIDES="weechat-python-plugin (= ${TERMUX_PKG_VERSION})"
TERMUX_SUBPKG_DEPEND_ON_PARENT=false
TERMUX_SUBPKG_DEPENDS="python, weechat-cjson (= ${TERMUX_PKG_FULLVERSION})"
