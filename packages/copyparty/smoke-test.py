#!/usr/bin/env python3
"""HTTP UI and byte-for-byte upload/download, restricted to a temporary volume."""
import tempfile
from smoke_support import *

with tempfile.TemporaryDirectory(prefix='copyparty-smoke-') as directory:
    work = Path(directory)
    env = environment(work)
    # JSON argv allows the same test against a staged host-Python launcher.
    command = json.loads(os.environ['COPYPARTY_COMMAND']) if 'COPYPARTY_COMMAND' in os.environ else ['copyparty']
    volume = work / 'files'
    volume.mkdir()
    number = port()
    base = f'http://127.0.0.1:{number}'
    # This disposable upload test intentionally uses temporary overlay/RAM storage.
    # Production launchers retain copyparty's default persistent-storage safety check.
    args = command + ['--wram', '-i', '127.0.0.1', '-p', str(number), '-v', str(volume) + ':/files:rw', '--http-only', '--no-ansi', '--no-thumb', '--no-crt', '-j', '1']
    with daemon(args, work, env, 'server') as process:
        ready(number, process)
        with HTTP.open(base + '/files/', timeout=10) as response:
            assert response.status == 200 and b'<html' in response.read().lower()
        payload = b'copyparty-byte-roundtrip\n' * 2048
        request = urllib.request.Request(base + '/files/payload.bin', payload, method='PUT', headers={'Content-Type': 'application/octet-stream'})
        with HTTP.open(request, timeout=20) as response:
            assert response.status in (200, 201, 204), response.status
        with HTTP.open(base + '/files/payload.bin', timeout=20) as response:
            assert response.read() == payload
        assert (volume / 'payload.bin').read_bytes() == payload
print('PASS copyparty: HTML UI, loopback upload/download and exact bytes on disk')
