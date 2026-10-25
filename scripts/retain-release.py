#!/usr/bin/env python3
"""Retain signed packages and corresponding sources from the previous release."""
import json
from pathlib import Path
import shutil
import subprocess
import sys


def retain(previous, destination):
    release = json.loads((previous / 'release.json').read_text())
    names = {asset['name'] for asset in release['assets']}
    payloads = sorted(name for name in names
                      if name.endswith(('.pkg.tar.xz', '-source.tar.gz')))
    if not any(name.endswith('.pkg.tar.xz') for name in payloads):
        raise ValueError('Previous release has no packages')
    # Verify every expected download, including signatures and collisions,
    # before copying anything. A glob alone could silently omit missing assets.
    for name in payloads:
        if Path(name).name != name:
            raise ValueError(f'Invalid release asset name: {name}')
        if name + '.sig' not in names:
            raise ValueError(f'Missing release signature: {name}')
        source = previous / name
        signature = previous / (name + '.sig')
        if not source.is_file() or not signature.is_file():
            raise ValueError(f'Missing downloaded asset or signature: {name}')
        subprocess.run(['gpg', '--batch', '--verify', str(signature), str(source)], check=True)
        target = destination / name
        if target.exists():
            # cmp streams large source archives without loading them in memory.
            subprocess.run(['cmp', str(source), str(target)], check=True)
    for name in payloads:
        if not (destination / name).exists():
            shutil.copy2(previous / name, destination / name)
            shutil.copy2(previous / (name + '.sig'), destination / (name + '.sig'))
    print(f'Retained {len(payloads)} verified package/source assets')


if __name__ == '__main__':
    retain(Path(sys.argv[1]), Path(sys.argv[2]))
