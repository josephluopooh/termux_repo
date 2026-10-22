#!/usr/bin/env bash
# Installation-only smoke test; no package downloads, game, or network service.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
tmp_root=$(cd "${TMPDIR:-/tmp}" && pwd -P)
stage=$(mktemp -d "$tmp_root/valheim-recipe.XXXXXXXX")
[[ "$stage" == "$tmp_root"/valheim-recipe.* && "$stage" != "$tmp_root" ]]
trap 'rm -rf -- "$stage"' EXIT
export TERMUX_PREFIX="$stage/usr"
export TERMUX_PKG_BUILDER_DIR="$root/packages/valheim-server"
source "$TERMUX_PKG_BUILDER_DIR/build.sh"
termux_step_configure
termux_step_make
termux_step_make_install
test -x "$TERMUX_PREFIX/bin/valheim-server"
test -f "$TERMUX_PREFIX/share/doc/valheim-server/README.md"
cmp "$TERMUX_PREFIX/bin/valheim-server" "$TERMUX_PKG_BUILDER_DIR/valheim-server"
cmp "$TERMUX_PREFIX/share/doc/valheim-server/README.md" "$TERMUX_PKG_BUILDER_DIR/README.md"
test "$(find "$stage" -type f | wc -l)" -eq 2
test "$TERMUX_PKG_PLATFORM_INDEPENDENT" = true
test "$TERMUX_PKG_SKIP_SRC_EXTRACT" = true
[[ "$TERMUX_PKG_DEPENDS" == *dotnet-runtime-9.0* ]]
[[ "$TERMUX_PKG_SUGGESTS" == *box64-glibc* ]]
echo 'PASS: recipe installs only the launcher and README, with no runtime download or service hook.'
