#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
# Disposable aarch64 Termux container only; preserve its signed repository policy.
pacman -Syu --noconfirm python ca-certificates dotnet-runtime-9.0 binutils \
    box64-glibc glibc gcc-libs-glibc libpulse-glibc libogg-glibc
pacman -Q python dotnet-runtime-9.0 box64-glibc glibc gcc-libs-glibc libpulse-glibc libogg-glibc
python -c 'import platform, sys; print("Native probe:", platform.system(), platform.machine(), sys.version)'
python -m unittest discover -s /repo/tests -p test_valheim_server.py -v
install -m700 /repo/packages/valheim-server/valheim-server "$PREFIX/bin/valheim-server"
python /repo/scripts/probe-native-servers-valheim.py
