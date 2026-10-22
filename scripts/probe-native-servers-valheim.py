"""Real anonymous download and no-proot Box64 startup in a disposable container."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

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
    os.environ['BOX64_ROLLING_LOG'] = '1'
    os.environ['BOX64_LOG'] = '1'
    for p in sorted(payload.rglob('*')):
        if p.is_file():
            with p.open('rb') as stream:
                is_elf = stream.read(4) == b'\x7fELF'
            if is_elf:
                result = subprocess.check_output(['greadelf', '-d', str(p)], text=True)
                needed = [line.strip() for line in result.splitlines() if 'NEEDED' in line or 'RPATH' in line or 'RUNPATH' in line]
                print('VALHEIM_ELF', p.relative_to(payload), json.dumps(needed), flush=True)
    for attempt in range(2):
        previous_logs = set((data / 'logs').glob('*.log')) if (data / 'logs').exists() else set()
        with (root / f'console-{attempt}.log').open('w+') as log:
            process = subprocess.Popen(['valheim-server', 'start'], stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT)
            ready = False
            try:
                end = time.monotonic() + 600
                while process.poll() is None and time.monotonic() < end:
                    logs = [p for p in (data / 'logs').glob('*.log') if p not in previous_logs]
                    text = '\n'.join(p.read_text(errors='replace') for p in logs)
                    if 'Game server connected' in text:
                        ready = True
                        break
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
            assert ready, 'Valheim did not reach Game server connected'
            assert process.returncode == 0, process.returncode
            assert list((data / 'worlds').rglob('*.db')), 'No saved world database'
            print('PASS: Valheim Box64 startup/save' if attempt == 0 else 'PASS: Valheim Box64 saved-world restart', flush=True)
    print('Client join and crossplay were not tested; no physical Android device was used.', flush=True)
