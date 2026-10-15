#!/usr/bin/env python3
"""Validate and assemble a complete Pacman snapshot (repo-add is authoritative)."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import sys

root = Path(sys.argv[1]).resolve()
new = sorted(root.glob('*.pkg.tar.xz'))
assert new, 'No packages to publish'
subprocess.run(['repo-add', str(root / 'termux_repo-aarch64.db.tar.gz'), *map(str, new)], check=True)
# GitHub release assets cannot be symlinks; Pacman downloads the short names.
for kind in ('db', 'files'):
    alias = root / f'termux_repo-aarch64.{kind}'
    alias.unlink(missing_ok=True)
    shutil.copyfile(root / f'termux_repo-aarch64.{kind}.tar.gz', alias)

with tarfile.open(root / 'termux_repo-aarch64.db') as tar:
    entries = {}
    for member in tar.getmembers():
        if member.name.endswith('/desc'):
            fields = {}
            for paragraph in tar.extractfile(member).read().decode().strip().split('\n\n'):
                lines = paragraph.splitlines()
                fields[lines[0].strip('%')] = lines[1:]
            name, filename = fields['NAME'][0], fields['FILENAME'][0]
            assert '/' not in filename and (root / filename).is_file()
            assert fields['ARCH'][0] in ('aarch64', 'any')
            assert fields['SHA256SUM'][0] == hashlib.sha256((root / filename).read_bytes()).hexdigest()
            entries[name] = fields
    assert {'cjson', 'weechat-cjson'} <= entries.keys()
    assert 'cjson' in entries['weechat-cjson']['DEPENDS']
    assert 'weechat' in entries['weechat-cjson']['CONFLICTS']
(root / 'repository-index.json').write_text(json.dumps(entries, indent=2) + '\n')
print(f'Validated Pacman database: {len(entries)} packages')
