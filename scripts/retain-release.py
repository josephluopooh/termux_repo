#!/usr/bin/env python3
"""Retain signed packages and corresponding sources from the previous release."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def safe_name(name):
    return (bool(name) and name not in ('.', '..') and Path(name).name == name
            and '\\' not in name and not any(ord(char) < 32 or ord(char) == 127 for char in name))


def parse_manifest(text):
    hashes = {}
    for line in text.splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match or not safe_name(match[2]):
            raise ValueError(f'Invalid checksum manifest entry: {line!r}')
        digest, name = match.groups()
        if name in hashes:
            raise ValueError(f'Duplicate checksum manifest entry: {name}')
        hashes[name] = digest
    if not hashes:
        raise ValueError('Previous checksum manifest is empty')
    return hashes


def load_manifest(previous):
    manifest, signature = previous / 'SHA256SUMS', previous / 'SHA256SUMS.sig'
    if not manifest.is_file() or not signature.is_file():
        raise ValueError('Missing previous checksum manifest or signature')
    subprocess.run(['gpg', '--batch', '--verify', str(signature), str(manifest)], check=True)
    return parse_manifest(manifest.read_text())


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def retain(previous, destination):
    hashes = load_manifest(previous)
    release = json.loads((previous / 'release.json').read_text())
    names = {asset['name'] for asset in release['assets']}
    for name in names:
        if not safe_name(name):
            raise ValueError(f'Invalid release asset name: {name}')
    payloads = sorted(name for name in hashes
                      if name.endswith(('.pkg.tar.xz', '-source.tar.gz')))
    if not any(name.endswith('.pkg.tar.xz') for name in payloads):
        raise ValueError('Previous release has no packages')
    suffixes = ('.pkg.tar.xz', '-source.tar.gz', '.pkg.tar.xz.sig', '-source.tar.gz.sig')
    expected = {name for name in hashes if name.endswith(suffixes)}
    for name in payloads:
        if name + '.sig' not in expected:
            raise ValueError(f'Missing checksum manifest signature: {name}')
    for name in expected:
        if name.endswith('.sig') and name[:-4] not in payloads:
            raise ValueError(f'Orphan checksum manifest signature: {name}')
    actual = {name for name in names if name.endswith(suffixes)}
    if expected - actual:
        raise ValueError(f'Missing release assets: {sorted(expected - actual)}')
    if actual - expected:
        raise ValueError(f'Unmanifested release assets: {sorted(actual - expected)}')
    # Verify every expected download, including signatures and collisions,
    # before copying anything. The signed manifest remains authoritative even
    # when an asset has been removed or renamed in the mutable release listing.
    for name in sorted(expected):
        source = previous / name
        if not source.is_file():
            raise ValueError(f'Missing downloaded asset: {name}')
        if sha256(source) != hashes[name]:
            raise ValueError(f'Checksum mismatch for previous asset: {name}')
    for name in payloads:
        source = previous / name
        signature = previous / (name + '.sig')
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
