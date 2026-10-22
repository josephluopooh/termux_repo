#!/usr/bin/env python3
"""Preserve dependency license/notice files and a manifest for the actual build.

Input is cargo metadata or the JSON stream from go list -deps. Nothing is fetched
or executed here. Cargo metadata includes host build dependencies as well.
"""
import json
from pathlib import Path
import re
import shutil
import sys

kind, source, destination = sys.argv[1:]
out = Path(destination)
out.mkdir(parents=True, exist_ok=True)
raw = Path(source).read_text()
modules = {}
if kind == 'cargo':
    for package in json.loads(raw)['packages']:
        if package['source'] is not None:
            modules[package['id']] = (package['name'] + '-' + package['version'], Path(package['manifest_path']).parent, package.get('license'), package.get('license_file'))
elif kind == 'go':
    decoder = json.JSONDecoder()
    while raw.strip():
        value, offset = decoder.raw_decode(raw.lstrip())
        raw = raw.lstrip()[offset:]
        module = value.get('Module', {})
        if module and not module.get('Main'):
            module = module.get('Replace') or module
            identity = module['Path'] + '@' + module.get('Version', 'local')
            modules[identity] = (identity, Path(module['Dir']), None, None)
else:
    raise SystemExit('expected cargo or go')

manifest = []
for identity, (label, directory, license_id, license_file) in sorted(modules.items()):
    safe = re.sub(r'[^a-zA-Z0-9._@+-]', '_', label)
    copied = []
    candidates = set()
    for path in directory.rglob('*'):
        if path.is_file() and (re.match(r'^(licen[cs]e|copying|copyright|notice|authors)([._-]|$)', path.name, re.I) or 'licenses' in [p.lower() for p in path.relative_to(directory).parts[:-1]]):
            candidates.add(path)
    if license_file:
        candidates.add(directory / license_file)
    for path in sorted(candidates):
        relative = path.relative_to(directory)
        target = out / safe / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        copied.append(str(relative).replace('\\', '/'))
    if not copied:
        raise SystemExit('No license/notice found for ' + identity)
    manifest.append({'dependency': identity, 'license': license_id, 'directory': safe, 'files': copied})
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Preserved notices for', len(manifest), 'dependencies')
