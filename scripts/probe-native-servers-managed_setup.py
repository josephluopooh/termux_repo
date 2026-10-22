"""Pinned upstream downloads and application-local native Mono adaptations."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
import zlib

PREFIX = Path('/data/data/com.termux/files/usr')
SUPPORT = Path(__file__).resolve().parent
RELEASES = {
    'tshock': ('6.2.1', 'https://github.com/Pryaxis/TShock/releases/download/v6.2.1/TShock-6.2.1-for-Terraria-1.4.5.8-linux-arm64-Release.zip', 'bc97babbff40e4291757b000486a82f9bbc2a0bc1360ec2a4213a84b1b772b98'),
    'tmodloader': ('2026.08.3.0', 'https://github.com/tModLoader/tModLoader/releases/download/v2026.08.3.0/tModLoader.zip', '61e865f3702b12ce4a26c5a90b9de99a12c65ffc228455eb3390ce54af1eab15'),
}

def target(root, name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('Unsafe archive name: ' + name)
    return root.joinpath(*path.parts)

def unzip(archive, root):
    with zipfile.ZipFile(archive) as z:
        if sum(x.file_size for x in z.infolist()) > 2_000_000_000:
            raise ValueError('Unexpected archive size')
        for item in z.infolist():
            out = target(root, item.filename)
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Archive symlinks are unsupported')
            if item.is_dir(): out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with z.open(item) as source, out.open('xb') as dest:
                    shutil.copyfileobj(source, dest)

def extract_bundle(data, root):
    # .NET single-file manifest v6: public Microsoft.NET.HostModel format.
    # The Linux apphost is parsed as data and never executed on Android.
    signature = bytes.fromhex('8b1202b96a612038727b930214d7a03213f5b9e6efae3318ee3b2dce24b36aae')
    location = data.find(signature)
    if location < 8 or data.find(signature, location + 1) >= 0: raise ValueError('Invalid bundle signature')
    header, = struct.unpack_from('<Q', data, location - 8)
    stream = io.BytesIO(data); stream.seek(header)
    def number(fmt):
        size = struct.calcsize(fmt); raw = stream.read(size)
        if len(raw) != size: raise ValueError('Truncated bundle')
        return struct.unpack(fmt, raw)
    def string():
        size = 0
        for i in range(5):
            byte, = number('<B'); size |= (byte & 127) << (i * 7)
            if byte < 128: break
        else: raise ValueError('Invalid string length')
        if size > 4096: raise ValueError('Oversize bundle name')
        return stream.read(size).decode('utf-8')
    major, minor, count = number('<III')
    if (major, minor) != (6, 0) or not 1 <= count <= 1000: raise ValueError('Unsupported bundle format')
    string(); number('<QQQQQ')
    names = []
    for _ in range(count):
        offset, size, compressed, kind = number('<QQQB'); name = string()
        out = target(root, name)
        if size > 100_000_000 or offset + (compressed or size) > header: raise ValueError('Invalid bundle extent')
        # Native libraries from the Linux bundle are deliberately excluded.
        if kind == 2: continue
        payload = data[offset:offset + (compressed or size)]
        if compressed:
            decoder = zlib.decompressobj(-15)
            payload = decoder.decompress(payload, size + 1)
            if not decoder.eof: raise ValueError('Invalid compressed payload')
        if len(payload) != size or payload[:4] == b'\x7fELF': raise ValueError('Invalid managed bundle entry')
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('xb') as dest: dest.write(payload)
        names.append(name)
    return names

def install(kind, base):
    version, url, digest = RELEASES[kind]
    installed = base / (version + '-native1')
    if (installed / '.complete.json').is_file():
        print('Already installed:', installed); return installed
    if installed.exists(): raise RuntimeError('Incomplete installation exists: ' + str(installed))
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.setup-', dir=base) as temporary:
        work = Path(temporary); archive = work / 'download.zip'; staged = work / 'server'; staged.mkdir()
        print('Downloading directly from upstream:', url, flush=True)
        request = urllib.request.Request(url, headers={'User-Agent': 'termux_repo/1.0 (native server setup)'})
        with urllib.request.urlopen(request, timeout=120) as source, archive.open('wb') as dest:
            shutil.copyfileobj(source, dest)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != digest: raise ValueError('Upstream checksum mismatch')
        unzip(archive, staged)
        if kind == 'tshock':
            packed = list(staged.glob('*.tar'))
            if len(packed) != 1: raise ValueError('Unexpected TShock archive')
            with tarfile.open(packed[0]) as tar:
                for item in tar:
                    out = target(staged, item.name)
                    if item.isdir(): out.mkdir(parents=True, exist_ok=True)
                    elif item.isfile():
                        out.parent.mkdir(parents=True, exist_ok=True)
                        with tar.extractfile(item) as source, out.open('xb') as dest: shutil.copyfileobj(source, dest)
                    else: raise ValueError('Unsupported tar entry')
            packed[0].unlink()
            extract_bundle((staged / 'TShock.Server').read_bytes(), staged)
            (staged / 'TShock.Server').unlink(); (staged / 'TShock.Installer').unlink()
            for item in (staged / 'bin').iterdir():
                if item.is_file(): shutil.copy2(item, staged / item.name)
            shutil.rmtree(staged / 'bin')
            assembly = staged / 'TerrariaServer.dll'
            for library in SUPPORT.glob('MonoMod.*.dll'): shutil.copy2(library, staged / library.name)
            # SQLitePCLRaw's e_sqlite3 provider uses standard sqlite3_* symbols.
            (staged / 'libe_sqlite3.so').symlink_to(PREFIX / 'lib/libsqlite3.so')
        else:
            assembly = staged / 'tModLoader.dll'
            cores = list((staged / 'Libraries').rglob('MonoMod.Core.dll'))
            if len(cores) != 1: raise ValueError('Unexpected MonoMod layout')
            shutil.copy2(SUPPORT / 'MonoMod.Core.dll', cores[0])
            # Only the headless Bionic SDL dependency can be loaded by this wrapper.
            native = staged / 'Libraries/Native'
            if native.exists(): shutil.rmtree(native)
            native = native / 'Linux-arm64'; native.mkdir(parents=True)
            (native / 'libSDL2-2.0.so').symlink_to(PREFIX / 'lib/libSDL2.so')
        env = dict(os.environ, DOTNET_ROLL_FORWARD='Major')
        subprocess.run(['dotnet', str(SUPPORT / 'managed-patch.dll'), kind, str(assembly)], check=True, env=env)
        (staged / '.complete.json').write_text(json.dumps({'upstream': version, 'sha256': digest, 'adaptation': 1}) + '\n')
        staged.rename(installed)
    print('Installed:', installed)
    return installed

def main(kind):
    base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / (kind + '-server')
    if not base.is_absolute(): raise ValueError('XDG_DATA_HOME must be absolute')
    version = RELEASES[kind][0]
    installed = base / (version + '-native1')
    args = sys.argv[1:]
    if not args or args[0] in ('--help', '-h'):
        print(f'{kind}-server install  Download and adapt the pinned upstream server.\n'
              f'{kind}-server run [server arguments]  Start with persistent state/worlds.\n'
              f'{kind}-server path  Print installation directory.\n'
              'Native Termux Mono/.NET; no proot or glibc. Steam/Workshop are not enabled.'); return
    if args == ['--version']: print(kind, version, 'native adaptation 1'); return
    if args == ['path']: print(installed); return
    if platform.machine() not in ('aarch64', 'arm64'): raise RuntimeError('aarch64 Termux is required')
    if args == ['install']: install(kind, base); return
    if args[0] != 'run': raise ValueError('Unknown command; see --help')
    if not (installed / '.complete.json').is_file(): raise RuntimeError(f'Run {kind}-server install first')
    state = base / 'state'; state.mkdir(exist_ok=True)
    (state / 'worlds').mkdir(exist_ok=True)
    if kind == 'tshock':
        plugins = state / 'ServerPlugins'; plugins.mkdir(exist_ok=True)
        for item in (installed / 'ServerPlugins').iterdir():
            if item.is_file() and not (plugins / item.name).exists(): shutil.copy2(item, plugins / item.name)
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = str(SUPPORT) + ':' + str(installed) + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    env['FNA_PLATFORM_BACKEND'] = 'NONE'
    env['DOTNET_ROLL_FORWARD'] = 'LatestMinor'
    assembly = installed / ('TShock.Server.dll' if kind == 'tshock' else 'tModLoader.dll')
    command = ['dotnet', str(assembly)] + (['-server'] if kind == 'tmodloader' else [])
    command += ['-savedirectory', str(state), '-world', str(state / 'worlds/world.wld'), '-worldname', 'world', '-autocreate', '1', '-noupnp', *args[1:]]
    os.chdir(state)
    os.execvpe('dotnet', command, env)

if __name__ == '__main__':
    main(sys.argv.pop(1))
