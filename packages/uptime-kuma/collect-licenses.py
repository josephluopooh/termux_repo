#!/usr/bin/env python3
"""Keep npm's published attribution, declarations, and locked integrity records.

Run before pruning: the dashboard incorporates development dependencies. No
license is inferred when an npm author publishes no standalone license file.
The manifest explicitly records those cases and preserves their README and
package metadata. Runtime modules also retain their complete published files.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

root, out = map(Path, sys.argv[1:])
lock = json.loads((root / 'package-lock.json').read_text())
out.mkdir(parents=True, exist_ok=True)
manifest = []
for relative, pinned in sorted(lock['packages'].items()):
    if not relative or not (root / relative / 'package.json').is_file():
        continue
    package = root / relative
    metadata = json.loads((package / 'package.json').read_text())
    assert pinned.get('integrity'), relative
    assert str(pinned.get('resolved', '')).startswith('https://registry.npmjs.org/'), relative
    label = re.sub(r'[^a-zA-Z0-9._@+-]', '_', relative)
    files, notices = [], []
    for path in package.rglob('*'):
        rel = path.relative_to(package)
        if 'node_modules' in rel.parts or not path.is_file() or path.is_symlink():
            continue
        notice = re.search(r'(^|[._-])(licen[cs]e|copying|copyright|notice|authors)([._-]|$)', path.name, re.I)
        documentation = len(rel.parts) == 1 and (path.name in ('package.json', 'component.json') or re.match(r'^readme([._-]|$)', path.name, re.I))
        if notice or documentation:
            target = out / label / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            files.append({'path': str(rel), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            if notice:
                notices.append(str(rel))
    declaration = metadata.get('license') or metadata.get('licenses')
    declaration_source = 'package.json'
    if not declaration and (package / 'component.json').is_file():
        declaration = json.loads((package / 'component.json').read_text()).get('license')
        declaration_source = 'component.json'
    manifest.append({'package': metadata.get('name', relative), 'version': pinned['version'],
                     'license': declaration, 'license_declaration_source': declaration_source,
                     'resolved': pinned['resolved'], 'integrity': pinned['integrity'],
                     'directory': label, 'standalone_notice_files': notices, 'files': files})
assert manifest
supplements = Path(__file__).with_name('supplemental-licenses')
supplement_manifest = json.loads((supplements / 'manifest.json').read_text())
for entry in supplement_manifest:
    source = supplements / entry['file']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == entry['sha256'], source
shutil.copytree(supplements, out / '_supplemental', dirs_exist_ok=True)
for entry in manifest:
    entry['supplemental_files'] = [item['file'] for item in supplement_manifest
                                   if item['name'] == entry['package'] and item['version'] == entry['version']]
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Preserved locked npm attribution for', len(manifest), 'packages')
