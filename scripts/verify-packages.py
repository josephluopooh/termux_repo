#!/usr/bin/env python3
"""Check actual Pacman metadata, Android ELF ABI, and cJSON relay linkage."""
import json
import os
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile

folder = Path(sys.argv[1])
selected = set(json.loads((Path(__file__).resolve().parents[1] / 'packages.json').read_text())['packages'])
metadata = {}
for archive in sorted(folder.glob('*.pkg.tar.xz')):
    with tarfile.open(archive) as tar:
        info = {}
        raw = tar.extractfile('.PKGINFO').read().decode()
        for line in raw.splitlines():
            if ' = ' in line:
                k, v = line.split(' = ', 1)
                info.setdefault(k, []).append(v)
        name, arch = info['pkgname'][0], info['arch'][0]
        assert info['pkgbase'][0] in selected, f'Unselected package in publication output: {name}'
        assert arch in ('aarch64', 'any'), (archive, arch)
        assert name not in metadata, f'Duplicate package: {name}'
        assert archive.name == f'{name}-{info["pkgver"][0]}-{arch}.pkg.tar.xz'
        for member in tar.getmembers():
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts, member.name
            assert (member.name == 'data' or member.name.startswith('data/')) or member.name in ('.PKGINFO', '.BUILDINFO', '.MTREE', '.INSTALL'), member.name
            if member.isfile():
                stream = tar.extractfile(member)
                if stream.read(4) == b'\x7fELF':
                    stream.seek(0)
                    with tempfile.NamedTemporaryFile() as elf:
                        elf.write(stream.read())
                        elf.flush()
                        abi = subprocess.check_output(['readelf', '-h', '-l', '-d', elf.name], text=True)
                    assert 'AArch64' in abi, (name, member.name, abi)
                    assert 'libc.so.6' not in abi and 'ld-linux' not in abi, (name, member.name)
                    if '/bin/' in member.name:
                        assert '/system/bin/linker64' in abi, (name, member.name, abi)
                    out = folder / 'evidence' / 'elf' / name
                    out.mkdir(parents=True, exist_ok=True)
                    (out / (member.name.replace('/', '_') + '.txt')).write_text(abi)
        if name in ('terraria-server', 'pumpkin-server'):
            assert arch == 'any' and '.INSTALL' not in tar.getnames()
            assert not any(m.name.endswith(('.exe', '.dll', '.so')) for m in tar.getmembers())
        if name == 'pumpkin-server':
            assert tar.getmember('data/data/com.termux/files/usr/bin/pumpkin-server').mode & 0o100
            assert tar.getmember('data/data/com.termux/files/usr/bin/pumpkin').linkname == 'pumpkin-server'
        if name == 'weechat-cjson':
            assert 'cjson' in info['depend']
            assert 'weechat' in info['conflict']
            assert any(p.startswith('weechat=4.10.1') for p in info['provides'])
            assert 'replaces' not in info
            for member_name in ('bin/weechat', 'bin/weechat-headless', 'lib/weechat/plugins/relay.so'):
                data = tar.extractfile('data/data/com.termux/files/usr/' + member_name).read()
                with tempfile.NamedTemporaryFile() as stream:
                    stream.write(data)
                    stream.flush()
                    output = subprocess.check_output(['readelf', '-h', '-l', '-d', '-Ws', stream.name], text=True)
                assert 'AArch64' in output
                assert 'libc.so.6' not in output and 'ld-linux' not in output
                if member_name.startswith('bin/'):
                    assert '/system/bin/linker64' in output
                else:
                    assert 'Shared library: [libcjson.so]' in output, output
                    assert 'cJSON_Parse' in output
                    assert b'/api/version' in data or b'relay_api' in data
                evidence = folder / 'evidence'
                evidence.mkdir(exist_ok=True)
                (evidence / (member_name.replace('/', '-') + '-elf.txt')).write_text(output)
        if name == 'toot':
            assert arch == 'any'
            assert '.INSTALL' not in tar.getnames(), 'toot must not have runtime install hooks'
            assert info['pkgver'][0].startswith('0.52.1-')
            assert {'ca-certificates', 'python>=3.11.5-0'} <= set(info['depend'])
            prefix = 'data/data/com.termux/files/usr/'
            launcher = tar.extractfile(prefix + 'bin/toot').read().decode()
            assert launcher.startswith('#!/data/data/com.termux/files/usr/bin/python -IBS\n')
            assert tar.getmember(prefix + 'bin/toot').mode & 0o100
            assert tar.getmember(prefix + 'lib/toot/certifi/cacert.pem').linkname == '/data/data/com.termux/files/usr/etc/tls/cert.pem'
            lock = tar.extractfile(prefix + 'share/doc/toot/requirements.txt').read().decode()
            distributions = {}
            for member in tar.getmembers():
                if member.name.startswith(prefix + 'lib/toot/') and member.name.endswith('.dist-info/METADATA'):
                    distribution = BytesParser().parsebytes(tar.extractfile(member).read())
                    distributions[distribution['Name'].lower().replace('-', '_')] = distribution['Version']
            for line in lock.splitlines():
                if not line or line.startswith('#'):
                    continue
                requirement = line.split()[0]
                distribution, version = requirement.split('==')
                normalized = distribution.lower().replace('-', '_')
                assert distributions[normalized] == version, requirement
            for member in tar.getmembers():
                if member.isfile():
                    assert not member.name.endswith(('.so', '.pyd', '.dll', '.exe', '.pyc')), member.name
                    assert not tar.extractfile(member).read(4).startswith(b'\x7fELF'), member.name
            assert not any('/site-packages/' in m.name for m in tar.getmembers())
        metadata[name] = {'filename': archive.name, **info}
required = set(os.environ.get('BUILD_PACKAGES', '').split()) if '--partial' in sys.argv else selected
assert required <= metadata.keys(), (required, metadata.keys())
for name, info in metadata.items():
    if name.startswith('weechat-cjson-'):
        assert any(d.startswith('weechat-cjson') for d in info['depend'])
        assert name.replace('weechat-cjson', 'weechat', 1) in info['conflict']
(folder / 'evidence').mkdir(exist_ok=True)
suffix = '-' + os.environ.get('BUILD_GROUP', 'all') if '--partial' in sys.argv else ''
(folder / 'evidence' / ('packages' + suffix + '.json')).write_text(json.dumps(metadata, indent=2) + '\n')
print('Verified:', ', '.join(metadata))
