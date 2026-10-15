#!/usr/bin/env python3
"""Check actual Pacman metadata, Android ELF ABI, and cJSON relay linkage."""
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile

folder = Path(sys.argv[1])
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
        assert arch in ('aarch64', 'any'), (archive, arch)
        assert name not in metadata, f'Duplicate package: {name}'
        assert archive.name == f'{name}-{info["pkgver"][0]}-{arch}.pkg.tar.xz'
        for member in tar.getmembers():
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts, member.name
            assert (member.name == 'data' or member.name.startswith('data/')) or member.name in ('.PKGINFO', '.BUILDINFO', '.MTREE', '.INSTALL'), member.name
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
        metadata[name] = {'filename': archive.name, **info}
assert {'cjson', 'weechat-cjson'} <= metadata.keys(), metadata.keys()
for name, info in metadata.items():
    if name.startswith('weechat-cjson-'):
        assert any(d.startswith('weechat-cjson') for d in info['depend'])
        assert name.replace('weechat-cjson', 'weechat', 1) in info['conflict']
(folder / 'evidence').mkdir(exist_ok=True)
(folder / 'evidence' / 'packages.json').write_text(json.dumps(metadata, indent=2) + '\n')
print('Verified:', ', '.join(metadata))
