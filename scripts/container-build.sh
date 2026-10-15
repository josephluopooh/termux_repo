#!/usr/bin/env bash
set -euo pipefail
cd /home/builder/termux-packages
# Trust only the upstream public key committed in the pinned source checkout.
gpg --batch --import packages/termux-keyring/termux-pacman.gpg
gpg --with-colons --fingerprint 998DE27318E867EA976BA877389CEED64573DFCA | grep -F 'fpr:::::::::998DE27318E867EA976BA877389CEED64573DFCA:'
mapfile -t packages < custom-packages.txt
for package in "${packages[@]}"; do
    ./build-package.sh -a aarch64 -I --format pacman --library bionic "$package"
done
mkdir -p output/evidence
cp "$HOME/.termux-build/weechat-cjson/build/CMakeCache.txt" output/evidence/weechat-CMakeCache.txt
cp "$HOME/.termux-build/weechat-cjson/build/compile_commands.json" output/evidence/ 2>/dev/null || true
grep -E '^ENABLE_(CJSON|RELAY|HEADLESS):BOOL=ON$' output/evidence/weechat-CMakeCache.txt | tee output/evidence/features.txt
test "$(wc -l < output/evidence/features.txt)" = 3
# Preserve the signed upstream dependency indexes and the exact downloaded bytes' hashes.
find "$HOME/.termux-build" -maxdepth 3 -type f \( -name '*-json' -o -name '*-json.gpg' \) -exec cp '{}' output/evidence/ \;
find "$HOME/.termux-build" -maxdepth 3 -type f -name '*.pkg.tar.xz' -exec sha256sum '{}' \; > output/evidence/dependency-sha256.txt
