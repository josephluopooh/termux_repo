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
python3 - <<'PY'
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

selected = set(json.loads(Path('packages.json').read_text())['packages'])
shutil.copytree('build/output/evidence', 'dist/evidence', dirs_exist_ok=True)
build_only = {}
for archive in sorted(Path('build/output').glob('*.pkg.tar.xz')):
    with tarfile.open(archive) as tar:
        info = dict(line.split(' = ', 1) for line in
                    tar.extractfile('.PKGINFO').read().decode().splitlines()
                    if ' = ' in line)
    # pkgbase also selects declared/automatic subpackages of a chosen recipe.
    # Fallback builds of unavailable official dependency versions are build
    # inputs; runtime dependencies must resolve from the official repositories.
    if info['pkgbase'] in selected:
        shutil.copy2(archive, Path('dist') / archive.name)
    else:
        build_only[archive.name] = {
            'pkgbase': info['pkgbase'], 'pkgver': info['pkgver'],
            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        }
Path('dist/evidence/build-only-packages.json').write_text(
    json.dumps(build_only, indent=2) + '\n')
PY
python3 scripts/verify-packages.py dist
cp sources.json packages.json dist/evidence/
git rev-parse HEAD > dist/evidence/commit.txt
