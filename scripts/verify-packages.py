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
                    if name == 'uptime-kuma':
                        assert member.name.endswith('/node_sqlite3.node'), member.name
                        assert 'Shared library: [libsqlite3.so]' in abi, abi
                        assert 'Shared library: [libc++_shared.so]' in abi, abi
                    if '/bin/' in member.name or '/libexec/' in member.name:
                        assert '/system/bin/linker64' in abi, (name, member.name, abi)
                        if name in ('ntfy', 'rainfrog', 'vaultwarden'):
                            assert 'Shared library: [libsqlite3.so]' in abi, (name, abi)
                        if name == 'vaultwarden':
                            # SQLite-only Vaultwarden uses OpenSSL for RSA;
                            # outbound TLS uses Rustls and need not link libssl.
                            assert 'Shared library: [libcrypto.so' in abi, abi
                        if name == 'presenterm':
                            assert 'Shared library: [libonig.so]' in abi, abi
                    out = folder / 'evidence' / 'elf' / name
                    out.mkdir(parents=True, exist_ok=True)
                    (out / (member.name.replace('/', '_') + '.txt')).write_text(abi)
        if name in ('terraria-server', 'pumpkin-server', 'tmodloader-server'):
            assert arch == 'any' and '.INSTALL' not in tar.getnames()
            assert not any(m.name.endswith(('.exe', '.dll', '.so')) for m in tar.getmembers())
        if name == 'terraria-managed-support':
            assert arch == 'aarch64' and '.INSTALL' not in tar.getnames()
            prefix = 'data/data/com.termux/files/usr/'
            members = tar.getnames()
            assert prefix + 'lib/terraria-managed-support/libmonomod-bionic.so' in members
            assert prefix + 'lib/terraria-managed-support/managed-patch.dll' in members
            assert not any(m.endswith(('TerrariaServer.exe', 'tModLoader.dll', 'OTAPI.dll')) for m in members)
            notices = prefix + 'share/doc/terraria-managed-support/dependency-licenses/manifest.json'
            assert json.loads(tar.extractfile(notices).read())
        if name == 'pumpkin-server':
            assert tar.getmember('data/data/com.termux/files/usr/bin/pumpkin-server').mode & 0o100
            assert tar.getmember('data/data/com.termux/files/usr/bin/pumpkin').linkname == 'pumpkin-server'
        if name in ('chisel', 'ntfy', 'rainfrog', 'presenterm', 'tailscale', 'uptime-kuma', 'adguardhome', 'vaultwarden'):
            manifest = 'data/data/com.termux/files/usr/share/doc/' + name + '/dependency-licenses/manifest.json'
            assert json.loads(tar.extractfile(manifest).read()), name
        if name in ('tailscale', 'uptime-kuma', 'adguardhome', 'vaultwarden'):
            assert arch == 'aarch64' and '.INSTALL' not in tar.getnames(), name
            prefix = 'data/data/com.termux/files/usr/'
            assert tar.getmember(prefix + 'share/doc/' + name + '/README.md').isfile()
            assert 'ca-certificates' in info['depend'], name
        if name == 'tailscale':
            for binary in ('bin/tailscale', 'libexec/tailscaled'):
                assert tar.extractfile(prefix + binary).read(4) == b'\x7fELF'
            assert '--tun=userspace-networking' in tar.extractfile(prefix + 'bin/tailscaled').read().decode()
        if name == 'vaultwarden':
            assert {'libsqlite', 'openssl'} <= set(info['depend'])
            assert tar.extractfile(prefix + 'libexec/vaultwarden').read(4) == b'\x7fELF'
            launcher = tar.extractfile(prefix + 'bin/vaultwarden').read().decode()
            assert 'ROCKET_ADDRESS:=127.0.0.1' in launcher and 'SIGNUPS_ALLOWED:=false' in launcher
            assert 'WEB_VAULT_ENABLED:=false' in launcher
            assert not any('/web-vault/' in m.name for m in tar.getmembers())
        if name == 'uptime-kuma':
            assert {'nodejs-lts', 'libsqlite', 'libc++'} <= set(info['depend'])
            addon = prefix + 'lib/uptime-kuma/node_modules/@louislam/sqlite3/lib/binding/napi-v6-android-arm64/node_sqlite3.node'
            assert tar.extractfile(addon).read(4) == b'\x7fELF'
            assert [m.name for m in tar.getmembers() if m.name.endswith('.node')] == [addon]
            assert tar.extractfile(prefix + 'lib/uptime-kuma/dist/index.html').read()
            assert json.loads(tar.extractfile(prefix + 'share/doc/uptime-kuma/package-lock.json').read())['lockfileVersion'] >= 2
        if name == 'adguardhome':
            assert tar.extractfile(prefix + 'libexec/adguardhome/AdGuardHome').read(4) == b'\x7fELF'
            defaults = tar.extractfile(prefix + 'share/adguardhome/AdGuardHome.yaml').read().decode()
            assert 'address: 127.0.0.1:3000' in defaults and 'port: 5353' in defaults
            assert 'bind_hosts: [127.0.0.1]' in defaults
            assert json.loads(tar.extractfile(prefix + 'share/doc/adguardhome/client-licenses/manifest.json').read())
        if name in ('adguardhome', 'vaultwarden'):
            assert any(folder.glob(name + '-*-source.tar.gz')), f'Missing corresponding source for {name}'
        if name == 'copyparty':
            assert arch == 'any' and '.INSTALL' not in tar.getnames()
            assert not any('/site-packages/' in m.name for m in tar.getmembers())
            for member in tar.getmembers():
                if member.isfile():
                    assert not member.name.endswith(('.so', '.pyd', '.dll', '.exe', '.pyc')), member.name
                    assert tar.extractfile(member).read(4) != b'\x7fELF', member.name
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
