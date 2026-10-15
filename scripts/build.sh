#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/prepare.py
image=$(python3 -c 'import json; print(json.load(open("sources.json"))["builder_image"])')
# No host networking, privileged container, added capabilities or credential mount.
docker run --rm --user root -v "$PWD/build:/home/builder/termux-packages" "$image" chown -R 1001:1001 /home/builder/termux-packages
docker run --rm -e CI=true -e SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)" \
    -v "$PWD/build:/home/builder/termux-packages" "$image" bash ./custom-build.sh
mkdir -p dist
cp -r build/output/. dist/
python3 scripts/verify-packages.py dist
cp sources.json packages.json dist/evidence/
git rev-parse HEAD > dist/evidence/commit.txt
