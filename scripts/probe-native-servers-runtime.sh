#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
server=$1
case "$server" in
    tshock) runtime=dotnet-runtime-9.0 ;;
    tmodloader|tmodloader-patched) runtime=dotnet-runtime-8.0 ;;
    vanilla-pumpkin) runtime=mono ;;
    *) exit 2 ;;
esac
pacman -Syu --noconfirm "$runtime" python libsqlite ca-certificates
if [[ $server == vanilla-pumpkin ]]; then
    pacman -S --noconfirm mono-libs binutils libc++
    install -m700 /recipes/terraria-server/terraria-server "$PREFIX/bin/terraria-server"
    install -m700 /recipes/pumpkin-server/pumpkin-server "$PREFIX/bin/pumpkin-server"
    ln -s pumpkin-server "$PREFIX/bin/pumpkin"
    exec python /tests/additions-smoke-test.py
fi
pacman -Q "$runtime" dotnet-host libsqlite
dotnet --info
printf 'Android build.prop present: '; test -f /system/build.prop && echo yes || echo no
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -r "/input/$server/." "$work/"
cd "$work"
if [[ $server == tmodloader-patched || $server == tshock ]]; then
    pacman -S --noconfirm clang
    if [[ $server == tmodloader-patched ]]; then
        test -f "$work/.native-patch-complete" || { echo 'Managed patch build failed; no patched server to test'; exit 1; }
        pacman -S --noconfirm sdl2
        ln -sf "$PREFIX/lib/libSDL2.so" "$work/Libraries/Native/Linux-arm64/libSDL2-2.0.so"
    fi
    clang -shared -fPIC /tests/probe-native-servers-cache.c -o "$work/libmonomod-bionic.so"
    # Application-local helper. No replacement of system libraries or OS spoofing.
    export LD_LIBRARY_PATH="$work${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    cp -r /input/detour "$work/detour"
    cp "$work/libmonomod-bionic.so" "$work/detour/"
    DOTNET_ROLL_FORWARD=Major dotnet "$work/detour/detour.dll"
fi
if [[ $server == tshock ]]; then
    # The build uses bundle_sqlite3 + official libsqlite, not e_sqlite3.
    # Keep the image's library search path: placing Termux ICU before the
    # AOSP ICU breaks libc's private versioned ICU calls in this test image.
    python /tests/probe-native-servers-monitor.py 19201 dotnet TShock.Server.dll -lang 1 -ip 127.0.0.1 -port 19201 \
        -noupnp -world "$work/test.wld" -autocreate 1 -maxplayers 2 < /dev/null
else
    export FNA_PLATFORM_BACKEND=NONE DOTNET_ROLL_FORWARD=LatestMinor
    # Direct managed headless startup. Never invoke the upstream shell bootstrap
    # which downloads a glibc runtime and overrides the native library path.
    python /tests/probe-native-servers-monitor.py 19202 dotnet tModLoader.dll -server -lang en-US -ip 127.0.0.1 \
        -port 19202 -noupnp -world "$work/test.wld" -autocreate 1 -maxplayers 2 < /dev/null
fi
