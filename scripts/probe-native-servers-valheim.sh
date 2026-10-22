#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
# Disposable aarch64 Termux container only; preserve its signed repository policy.
pacman -Syu --noconfirm python ca-certificates dotnet-runtime-9.0 binutils strace \
    box64-glibc glibc gcc-libs-glibc libpulse-glibc libogg-glibc zlib-glibc
pacman -Q python dotnet-runtime-9.0 box64-glibc glibc gcc-libs-glibc libpulse-glibc libogg-glibc
python -c 'import platform, sys; print("Native probe:", platform.system(), platform.machine(), sys.version)'
python -m unittest discover -s /repo/tests -p test_valheim_server.py -v
install -m700 /repo/packages/valheim-server/valheim-server "$PREFIX/bin/valheim-server"
# Diagnostic only: file lookup metadata, never TLS plaintext or network payloads.
# Trace the monitor itself so its child PIDs and signal forwarding stay intact.
trace_file=$(mktemp "$PREFIX/tmp/valheim-files.XXXXXX")
finish_trace() {
    local status=$?
    trap - EXIT
    python /repo/scripts/probe-native-servers-valheim-trace.py "$trace_file" || true
    rm -f -- "$trace_file"
    exit "$status"
}
trap finish_trace EXIT
strace -f -qq -s 256 -e trace=%file,get_robust_list,set_robust_list \
    -o "$trace_file" python /repo/scripts/probe-native-servers-valheim.py
