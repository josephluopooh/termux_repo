#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
server=$1
case "$server" in
    tshock) runtime=dotnet-runtime-9.0 ;;
    tmodloader) runtime=dotnet-runtime-8.0 ;;
    *) exit 2 ;;
esac
pacman -Syu --noconfirm "$runtime" python libsqlite ca-certificates
pacman -Q "$runtime" dotnet-host libsqlite
dotnet --info
printf 'Android build.prop present: '; test -f /system/build.prop && echo yes || echo no
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -r "/input/$server/." "$work/"
cd "$work"
if [[ $server == tshock ]]; then
    # The build uses bundle_sqlite3 + official libsqlite, not e_sqlite3.
    export LD_LIBRARY_PATH="$PWD:$PREFIX/lib"
    python /tests/probe-native-servers-monitor.py 19201 dotnet TShock.Server.dll -lang 1 -ip 127.0.0.1 -port 19201 \
        -noupnp -world "$work/test.wld" -autocreate 1 -maxplayers 2 < /dev/null
else
    export FNA_PLATFORM_BACKEND=NONE DOTNET_ROLL_FORWARD=LatestMinor
    # Direct managed headless startup. Never invoke the upstream shell bootstrap
    # which downloads a glibc runtime and overrides the native library path.
    python /tests/probe-native-servers-monitor.py 19202 dotnet tModLoader.dll -server -lang en-US -ip 127.0.0.1 \
        -port 19202 -noupnp -world "$work/test.wld" -autocreate 1 -maxplayers 2 < /dev/null
fi
