"""Real anonymous download and no-proot Box64 startup in a disposable container."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time


CONNECTED = re.compile(r'(?m)^(?:\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}: )?Game server connected[ \t]*$')
CONNECT_FAILED = re.compile(r'(?m)^(?:\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}: )?Game server connected failed\b.*$')


def connected(text):
    """A failed connection or stale success is not server readiness."""
    successes = list(CONNECTED.finditer(text))
    failures = list(CONNECT_FAILED.finditer(text))
    return bool(successes) and (not failures or successes[-1].start() > failures[-1].start())


def world_files(worlds):
    databases = list(worlds.rglob('NativeProbe.db'))
    assert len(databases) == 1, f'Expected one saved NativeProbe.db, found {databases}'
    database = databases[0]
    metadata = database.with_suffix('.fwl')
    assert database.stat().st_size > 0, 'Saved world database is empty'
    assert metadata.is_file() and metadata.stat().st_size > 0, 'Saved world metadata is missing/empty'
    return database, metadata


with tempfile.TemporaryDirectory(prefix='valheim-native-probe-') as temporary:
    root = Path(temporary)
    os.environ['XDG_CONFIG_HOME'] = str(root / 'config')
    os.environ['XDG_DATA_HOME'] = str(root / 'data')
    config = root / 'config/valheim-server/config.json'
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps(dict(name='Termux CI', world='NativeProbe', password='temporary-ci-pass',
                                      port=19230, public=False, crossplay=False)))
    subprocess.run(['valheim-server', 'doctor'], check=True)
    # stdin is closed: no credentials or agreement prompt is answered automatically.
    subprocess.run(['valheim-server', 'setup'], check=True, stdin=subprocess.DEVNULL, timeout=900)
    data = root / 'data/valheim-server'
    generation = json.loads((data / 'current.json').read_text())['generation']
    payload = data / generation
    os.environ['SSL_CERT_FILE'] = '/data/data/com.termux/files/usr/etc/tls/cert.pem'
    os.environ['BOX64_DYNAREC_STRONGMEM'] = '2'
    os.environ['BOX64_DYNAREC_BIGBLOCK'] = '0'
    os.environ['BOX64_DYNAREC_SAFEFLAGS'] = '2'
    # v0.4.4 library.c otherwise resets STRONGMEM to 1 when this Mono loads.
    # Keep the conservative settings explicit; this only affects this probe.
    os.environ['BOX64_DYNAREC_BLEEDING_EDGE'] = '0'
    os.environ['BOX64_ROLLING_LOG'] = '1'
    # Print the original fault even when Mono installs its own crash handler.
    os.environ['BOX64_SHOWSEGV'] = '1'
    os.environ['BOX64_SHOWBT'] = '1'
    os.environ['BOX64_LOG'] = '1'
    for p in sorted(payload.rglob('*')):
        if p.is_file():
            with p.open('rb') as stream:
                is_elf = stream.read(4) == b'\x7fELF'
            if is_elf:
                result = subprocess.check_output(['greadelf', '-d', str(p)], text=True)
                needed = [line.strip() for line in result.splitlines() if 'NEEDED' in line or 'RPATH' in line or 'RUNPATH' in line]
                print('VALHEIM_ELF', p.relative_to(payload), json.dumps(needed), flush=True)
    saved_world = None
    for attempt in range(2):
        if saved_world is not None:
            database, metadata = world_files(data / 'worlds')
            assert database.relative_to(data) == saved_world['database'], 'Saved world path changed before restart'
            assert hashlib.sha256(metadata.read_bytes()).hexdigest() == saved_world['metadata_sha256'], 'World identity changed before restart'
        previous_logs = set((data / 'logs').glob('*.log')) if (data / 'logs').exists() else set()
        with (root / f'console-{attempt}.log').open('w+') as log:
            process = subprocess.Popen(['valheim-server', 'start'], stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT)
            ready = False
            connected_since = None
            observed_failures = 0
            try:
                end = time.monotonic() + 600
                while process.poll() is None and time.monotonic() < end:
                    logs = sorted(p for p in (data / 'logs').glob('*.log') if p not in previous_logs)
                    text = '\n'.join(p.read_text(errors='replace') for p in logs)
                    failures = len(CONNECT_FAILED.findall(text))
                    if failures > observed_failures:
                        connected_since = None
                        observed_failures = failures
                    if connected(text):
                        if connected_since is None:
                            connected_since = time.monotonic()
                            print(f'Valheim attempt {attempt + 1}: exact connected message; checking 30 seconds of stable operation', flush=True)
                        elif time.monotonic() - connected_since >= 30:
                            ready = True
                            break
                    else:
                        # A later failed connection invalidates an earlier success.
                        connected_since = None
                    time.sleep(2)
                if ready:
                    process.send_signal(signal.SIGINT)
                    process.wait(120)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(30)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
                log.seek(0)
                print(log.read(), flush=True)
                for p in (data / 'logs').glob('*.log'):
                    print(p.name, p.read_text(errors='replace'), flush=True)
            assert ready, 'Valheim did not reach and sustain an exact Game server connected success for 30 seconds'
            assert process.returncode == 0, process.returncode
            database, metadata = world_files(data / 'worlds')
            metadata_sha256 = hashlib.sha256(metadata.read_bytes()).hexdigest()
            if saved_world is not None:
                assert database.relative_to(data) == saved_world['database'], 'Restart saved a different world database'
                assert metadata_sha256 == saved_world['metadata_sha256'], 'Restart changed the saved world identity'
                assert database.stat().st_mtime_ns > saved_world['database_mtime_ns'], 'Restart did not save the existing world database'
            saved_world = dict(database=database.relative_to(data), metadata_sha256=metadata_sha256,
                               database_mtime_ns=database.stat().st_mtime_ns)
            print('VALHEIM_WORLD', str(saved_world['database']), 'bytes=', database.stat().st_size,
                  'metadata_sha256=', metadata_sha256, flush=True)
            print('PASS: Valheim Box64 startup/save' if attempt == 0 else 'PASS: Valheim Box64 saved-world restart', flush=True)
    print('Client join and crossplay were not tested; no physical Android device was used.', flush=True)
