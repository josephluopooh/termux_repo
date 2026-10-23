#!/usr/bin/env python3
"""Archive exact corresponding GPL source and dependencies used in this build."""
import io
import json
from pathlib import Path
import sys
import tarfile

source, recipe, dependency_json, modcache, output = map(Path, sys.argv[1:])
output.parent.mkdir(parents=True, exist_ok=True)
raw = dependency_json.read_text()
modules = {}
decoder = json.JSONDecoder()
while raw.strip():
    value, offset = decoder.raw_decode(raw.lstrip())
    raw = raw.lstrip()[offset:]
    module = value.get('Module', {})
    if module and not module.get('Main'):
        module = module.get('Replace') or module
        modules[module['Path']] = Path(module['Dir'])
with tarfile.open(output, 'w:gz') as archive:
    def source_filter(info):
        parts = Path(info.name).parts
        if '.git' in parts or '__pycache__' in parts:
            return None
        if info.name in ('adguardhome/AdGuardHome', 'adguardhome/build') or info.name.startswith('adguardhome/build/'):
            return None
        return info
    # npm dependencies are included to retain all source entering bundled JS.
    archive.add(source, arcname='adguardhome', filter=source_filter)
    archive.add(recipe, arcname='termux-recipe', filter=source_filter)
    for directory in sorted(set(modules.values())):
        archive.add(directory, arcname='go-modules/' + str(directory.relative_to(modcache)))
    # Module graph metadata is needed even for modules without linked packages.
    for path in (modcache / 'cache/download').rglob('*.mod'):
        archive.add(path, arcname='go-modules/' + str(path.relative_to(modcache)))
    text = b'''AdGuard Home v0.107.79 corresponding source for this Termux build.
Upstream source, Android recipe, locked frontend dependencies, and runtime Go
module source are included. Install Go >=1.26.6, Node 24 and an Android NDK.
The release source commit pins the Termux builder and toolchain in sources.json.
Use termux-recipe/build.sh within that builder to reproduce the Android build.
The recipe runs npm ci using client/package-lock.json (integrity-verified) and
builds the stable client before go build. The frontend dependencies already in
client/node_modules also allow npm run --prefix client build-prod directly.
Go dependencies are provided under go-modules with go.mod/go.sum in the source.
Upstream licensing is LICENSE.txt; dependency licenses are in their sources.
The standard Termux runtime dependencies are separate official packages.
'''
    info = tarfile.TarInfo('BUILD-SOURCE.txt')
    info.size = len(text)
    archive.addfile(info, io.BytesIO(text))
print('Corresponding source:', output, output.stat().st_size, 'bytes')
