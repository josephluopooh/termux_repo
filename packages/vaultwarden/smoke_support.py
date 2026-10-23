"""Package-local smoke support; temporary state and loopback listeners only."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

def environment(work):
    # Preserve runtime plumbing, never a caller's Vaultwarden configuration,
    # database paths, SMTP/OIDC credentials or server signing-key locations.
    env = {key: os.environ[key] for key in (
        'PATH', 'LD_LIBRARY_PATH', 'LD_PRELOAD', 'TMPDIR', 'TMP', 'TEMP',
        'PREFIX', 'ANDROID_ROOT', 'ANDROID_DATA', 'LANG', 'LC_ALL', 'TZ',
    ) if key in os.environ}
    # Child processes must not read or write the user's real configuration.
    for variable, name in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache')]:
        path = work / name
        path.mkdir(exist_ok=True)
        env[variable] = str(path)
    env['NO_COLOR'] = '1'
    return env

def run(args, work, env):
    return subprocess.check_output(args, cwd=work, env=env, text=True, stderr=subprocess.STDOUT, timeout=30)

@contextmanager
def daemon(args, work, env, name):
    with (work / (name + '.log')).open('w+') as log:
        process = subprocess.Popen(args, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        try:
            yield process
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(10)
            log.seek(0)
            print(log.read()[-12000:])

def ready(number, process):
    end = time.monotonic() + 30
    while time.monotonic() < end:
        if process.poll() is not None:
            raise AssertionError('Server exited: ' + str(process.returncode))
        try:
            with socket.create_connection(('127.0.0.1', number), timeout=1):
                return
        except OSError:
            time.sleep(.1)
    raise AssertionError('Loopback server did not become ready')
