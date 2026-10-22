#!/usr/bin/env python3
"""Preserve dependency license/notice files and a manifest for the actual build.

Input is cargo metadata or the JSON stream from go list -deps. Missing crate
notices are read from the exact Git revision recorded in the crate archive.
No downloaded code is executed. Cargo metadata includes build dependencies.
"""
import json
from pathlib import Path
import re
import shutil
import sys
import hashlib
import tomllib
import urllib.request
import urllib.error

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
    fetched = []
    if not copied and kind == 'cargo':
        vcs = directory / '.cargo_vcs_info.json'
        package = tomllib.loads((directory / 'Cargo.toml').read_text())['package']
        repository = package.get('repository', '').removesuffix('.git').rstrip('/')
        commit = json.loads(vcs.read_text()).get('git', {}).get('sha1', '') if vcs.is_file() else ''
        if re.fullmatch(r'https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) and re.fullmatch(r'[0-9a-f]{40}', commit):
            for filename in ('LICENSE', 'LICENSE.txt', 'LICENSE.md', 'LICENSE-MIT', 'LICENSE-APACHE', 'COPYING'):
                url = repository.replace('https://github.com/', 'https://raw.githubusercontent.com/') + '/' + commit + '/' + filename
                try:
                    with urllib.request.urlopen(url, timeout=30) as response: content = response.read(262145)
                except urllib.error.HTTPError as error:
                    if error.code == 404: continue
                    raise
                if len(content) > 262144: raise SystemExit('Oversize license: ' + url)
                target = out / safe / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content); copied.append(filename)
                fetched.append({'url': url, 'sha256': hashlib.sha256(content).hexdigest()})
    if not copied:
        raise SystemExit('No license/notice found for ' + identity)
    manifest.append({'dependency': identity, 'license': license_id, 'directory': safe, 'files': copied, 'upstream_notices': fetched})
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Preserved notices for', len(manifest), 'dependencies')
