#!/usr/bin/env python3
"""Materialize pinned upstream recipes and overlay this repository's packages."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
config = json.loads((root / 'sources.json').read_text())
packages = json.loads((root / 'packages.json').read_text())['packages']
assert packages and len(packages) == len(set(packages))
assert all(re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', p) for p in packages)
revision = os.environ.get('REPO_REVISION', '1')
assert re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', revision)
build = root / 'build'
subprocess.run(['git', 'clone', '--no-checkout', '--filter=blob:none', config['upstream_url'], str(build)], check=True)
subprocess.run(['git', '-C', str(build), 'checkout', '--detach', config['upstream_commit']], check=True)
for directory in (root / 'packages').iterdir():
    if directory.is_dir():
        shutil.copytree(directory, build / 'packages' / directory.name, dirs_exist_ok=True)
for name in packages:
    recipe = build / 'packages' / name / 'build.sh'
    assert recipe.is_file(), f'Missing recipe: {name}'
    # Unique, ordered pkgrel avoids replacing cached package bytes on rebuild.
    with recipe.open('a') as stream:
        stream.write(f'\nTERMUX_PKG_REVISION="{revision}"\n')
shutil.copy(root / 'scripts' / 'container-build.sh', build / 'custom-build.sh')
(build / 'custom-packages.txt').write_text('\n'.join(packages) + '\n')
