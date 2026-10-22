"""Report real native startup, preserving the failure output when unsupported."""
import pathlib
import socket
import subprocess
import sys
import time

port = int(sys.argv[1])
with open('native-startup.log', 'w+') as log:
    process = subprocess.Popen(sys.argv[2:], stdin=subprocess.PIPE, stdout=log,
                               stderr=subprocess.STDOUT, text=True)
    success = False
    try:
        end = time.monotonic() + 180
        while time.monotonic() < end:
            if process.poll() is not None:
                break
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=1):
                    success = True
                    break
            except OSError:
                time.sleep(1)
        if success:
            process.stdin.write('exit\n'); process.stdin.flush()
            process.wait(60)
            success = process.returncode == 0 and pathlib.Path('test.wld').is_file()
    finally:
        if process.poll() is None:
            process.terminate()
            try: process.wait(15)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        log.seek(0)
        print(log.read(), flush=True)
    print('NATIVE_SERVER_RESULT:', 'PASS' if success else 'FAILED', 'exit=', process.returncode)
    raise SystemExit(0 if success else 1)
