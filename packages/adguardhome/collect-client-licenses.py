#!/usr/bin/env python3
"""Preserve locked npm module notices, including source-only build tools."""
import json
import hashlib
from pathlib import Path
import re
import shutil
import sys

client, destination = map(Path, sys.argv[1:])
lock = json.loads((client / 'package-lock.json').read_text())
destination.mkdir(parents=True, exist_ok=True)
supplement_root = Path(__file__).with_name('client-license-supplements')
supplements = json.loads((supplement_root / 'manifest.json').read_text())
for row in supplements:
    assert hashlib.sha256((supplement_root / row['file']).read_bytes()).hexdigest() == row['sha256']
shutil.copytree(supplement_root, destination / 'supplements', dirs_exist_ok=True)
manifest = []
for relative, expected in sorted(lock['packages'].items()):
    if not relative or expected.get('link'):
        continue
    root = client / relative
    if not root.exists():
        assert expected.get('optional'), relative
        continue
    package = json.loads((root / 'package.json').read_text())
    assert package['version'] == expected['version'], relative
    identity = relative.replace('node_modules/', '').replace('/', '_')
    target = destination / identity
    target.mkdir(exist_ok=True)
    shutil.copyfile(root / 'package.json', target / 'package.json')
    copied = []
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if 'node_modules' in rel.parts or not path.is_file():
            continue
        if re.match(r'^(licen[cs]e|copying|copyright|notice|authors)([._-]|$)', path.name, re.I):
            out = target / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out)
            copied.append(str(rel))
    if not copied:
        # Some npm packages put their grant in README, or publish only a license
        # declaration. Preserve that original metadata; source is also archived.
        for path in root.iterdir():
            if path.is_file() and path.name.lower().startswith('readme'):
                shutil.copyfile(path, target / path.name)
                copied.append(path.name)
    license_id = package.get('license', package.get('licenses'))
    if not copied and not license_id:
        raise SystemExit('No license information: ' + relative)
    manifest.append({'package': package.get('name'), 'version': package['version'], 'license': license_id, 'files': copied, 'directory': identity})
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Preserved client notices:', len(manifest))
