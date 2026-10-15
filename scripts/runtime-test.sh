#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
# Runs only in a disposable Termux-Pacman container, never on a user's device.
# Keep the image's existing signature policy: local build artifacts are allowed
# by its LocalFileSigLevel=Optional; signed upstream databases remain required.
pacman -Syu --noconfirm
pacman -U --noconfirm /packages/*.pkg.tar.xz
pacman -Q cjson weechat-cjson
weechat-headless --version
work=$(mktemp -d)
server_pid=''
client_pid=''
cleanup() {
    result=$?
    if (( result != 0 )); then cat "$work"/*.log 2>/dev/null || true; fi
    [[ -z $client_pid ]] || kill "$client_pid" 2>/dev/null || true
    [[ -z $server_pid ]] || kill "$server_pid" 2>/dev/null || true
    rm -rf "$work"
    return "$result"
}
trap cleanup EXIT
weechat-headless --stdout -d "$work/server" -r '/set relay.network.bind_address 127.0.0.1;/set relay.network.password ci-loopback-only;/relay add api 19001' > "$work/server.log" 2>&1 &
server_pid=$!
for _attempt in {1..30}; do
    if curl --fail --silent -u plain:ci-loopback-only http://127.0.0.1:19001/api/version > "$work/version.json"; then break; fi
    sleep 1
done
cat "$work/version.json"
python - "$work/version.json" <<'PY'
import json, sys
version = json.load(open(sys.argv[1]))
assert version['weechat_version'] == '4.10.1', version
assert version['relay_api_version'], version
PY
status=$(curl --silent -o /dev/null -w '%{http_code}' http://127.0.0.1:19001/api/version)
test "$status" = 401
# Exercise WeeChat itself as an API remote client over a loopback websocket.
weechat-headless --stdout -d "$work/client" -r '/remote add test http://127.0.0.1:19001 -password=ci-loopback-only;/remote connect test' > "$work/client.log" 2>&1 &
client_pid=$!
for _attempt in {1..30}; do
    if grep -Fq 'remote[test]: WeeChat: 4.10.1' "$work/client.log"; then break; fi
    sleep 1
done
cat "$work/client.log"
# Source and compiled-symbol checks also prove that remote API code is included.
grep -F 'remote[test]: WeeChat: 4.10.1' "$work/client.log"
echo 'PASS: Pacman install, Android/aarch64 startup, authenticated API JSON, HTTP 401 without credentials, remote connection'
