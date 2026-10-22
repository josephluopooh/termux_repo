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
assert config['architecture'] == 'aarch64', 'Adding an architecture requires ABI/runtime validation'
assert config['android_api'] == 24
assert config['prefix'] == '/data/data/com.termux/files/usr'
packages = json.loads((root / 'packages.json').read_text())['packages']
if os.environ.get('BUILD_PACKAGES'):
    requested = os.environ['BUILD_PACKAGES'].split()
    assert set(requested) <= set(packages), requested
    packages = requested
assert packages and len(packages) == len(set(packages))
assert all(re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', p) for p in packages)
revision = os.environ.get('REPO_REVISION', '1')
assert re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', revision)
build = root / 'build'
subprocess.run(['git', 'clone', '--no-checkout', '--filter=blob:none', config['upstream_url'], str(build)], check=True)
subprocess.run(['git', '-C', str(build), 'checkout', '--detach', config['upstream_commit']], check=True)
for patch in sorted((root / 'patches').glob('*.patch')):
    subprocess.run(['git', '-C', str(build), 'apply', '--check', str(patch)], check=True)
    subprocess.run(['git', '-C', str(build), 'apply', str(patch)], check=True)
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

# Exercise upstream's real dependency parser before pulling the large image.
for name in packages:
    subprocess.run(['./scripts/buildorder.py', '-i', 'packages/' + name,
                    'packages', 'root-packages', 'x11-packages'],
                   cwd=build, stdout=subprocess.DEVNULL, check=True)
