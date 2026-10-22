#!/usr/bin/env python3
"""Functional checks inside a disposable native aarch64 Termux container."""
from contextlib import contextmanager
import fcntl
import http.server
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import socket
import sqlite3
import struct
import subprocess
import tempfile
import termios
import threading
import time
import urllib.request

PREFIX = Path('/data/data/com.termux/files/usr')

def run(args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(args, check=True, timeout=kwargs.pop('timeout', 120), **kwargs)

def wait_port(port, process=None, timeout=60):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if process is not None and process.poll() is not None:
            raise AssertionError(f'Process exited before port {port}: {process.returncode}')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return
        except OSError:
            time.sleep(.3)
    raise AssertionError(f'Port {port} did not become ready')

@contextmanager
def daemon(args, directory, env=None):
    logpath = directory / (Path(args[0]).name + '.log')
    with logpath.open('w+') as log:
        process = subprocess.Popen(args, cwd=directory, env=env, stdin=subprocess.PIPE,
                                   stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            yield process
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(15)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(10)
            log.seek(0)
            print(log.read()[-16000:], flush=True)

def tui(args, directory, expected, quit_keys=b'q', timeout=40):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 36, 140, 1120, 576))
    environment = {**os.environ, 'TERM': 'xterm-256color', 'COLORTERM': 'truecolor'}
    process = subprocess.Popen(args, cwd=directory, env=environment,
                               stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
    os.close(slave)
    output = b''
    try:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if select.select([master], [], [], .2)[0]:
                try: chunk = os.read(master, 65536)
                except OSError: break
                output += chunk
                # Respond to terminal cursor-position requests from crossterm.
                if b'\x1b[6n' in chunk: os.write(master, b'\x1b[1;1R')
                if expected.encode() in re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output):
                    os.write(master, quit_keys)
                    break
            if process.poll() is not None: break
        clean = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output).decode(errors='replace')
        assert expected in clean, (args, process.poll(), clean[-5000:])
        assert 'panicked at' not in clean, clean
        print('PASS: interactive render:', args[0], expected, flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try: process.wait(10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        os.close(master)

with tempfile.TemporaryDirectory(prefix='termux-additions-') as temporary:
    work = Path(temporary)
    os.environ['HOME'] = str(work / 'home')
    os.environ['XDG_CONFIG_HOME'] = str(work / 'config')
    os.environ['XDG_DATA_HOME'] = str(work / 'data')
    for name in ('home', 'config', 'data'): (work / name).mkdir()

    # Candidate tests remain available, but require an explicit later selection.
    if os.environ.get('RUN_CANDIDATES') == '1':
        # Real loopback HTTP payload forwarded through both tunneling tools.
        payload = b'termux-native-tunnel-check\n'
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(payload)
            def log_message(self, *_): pass
        http = http.server.ThreadingHTTPServer(('127.0.0.1', 19100), Handler)
        threading.Thread(target=http.serve_forever, daemon=True).start()
        with daemon(['chisel', 'server', '--host', '127.0.0.1', '--port', '19101', '--auth', 'ci:loopback-only'], work) as server:
            wait_port(19101, server)
            clientdir = work / 'chisel-client'; clientdir.mkdir()
            with daemon(['chisel', 'client', '--auth', 'ci:loopback-only', 'http://127.0.0.1:19101', '127.0.0.1:19102:127.0.0.1:19100'], clientdir) as client:
                wait_port(19102, client)
                assert urllib.request.urlopen('http://127.0.0.1:19102/', timeout=10).read() == payload
        print('PASS: chisel authenticated tunnel forwards HTTP payload', flush=True)

        (work / 'server.toml').write_text('[server]\nbind_addr="127.0.0.1:19103"\n[server.services.test]\ntoken="ci-loopback-only"\nbind_addr="127.0.0.1:19104"\n')
        (work / 'client.toml').write_text('[client]\nremote_addr="127.0.0.1:19103"\n[client.services.test]\ntoken="ci-loopback-only"\nlocal_addr="127.0.0.1:19100"\n')
        with daemon(['rathole', str(work / 'server.toml')], work) as server:
            wait_port(19103, server)
            clientdir = work / 'rathole-client'; clientdir.mkdir()
            with daemon(['rathole', str(work / 'client.toml')], clientdir) as client:
                wait_port(19104, client)
                assert urllib.request.urlopen('http://127.0.0.1:19104/', timeout=10).read() == payload
        http.shutdown()
        print('PASS: rathole authenticated tunnel forwards HTTP payload', flush=True)

        paste = work / 'paste'; paste.mkdir()
        config = (PREFIX / 'share/doc/rustypaste/config.toml').read_text().replace('127.0.0.1:8000', '127.0.0.1:19105')
        (paste / 'config.toml').write_text(config)
        with daemon(['rustypaste'], paste) as process:
            wait_port(19105, process)
            body = b'--termux-ci\r\nContent-Disposition: form-data; name="file"; filename="test.txt"\r\nContent-Type: text/plain\r\n\r\n' + payload + b'\r\n--termux-ci--\r\n'
            request = urllib.request.Request('http://127.0.0.1:19105/', body, {'Content-Type': 'multipart/form-data; boundary=termux-ci'})
            url = urllib.request.urlopen(request, timeout=10).read().decode().strip()
            assert urllib.request.urlopen(url, timeout=10).read() == payload
        print('PASS: rustypaste HTTP upload/download round trip', flush=True)

        irc = work / 'irc'; irc.mkdir()
        config = (PREFIX / 'share/doc/ergo/default.yaml').read_text().replace('127.0.0.1:6667', '127.0.0.1:19106').replace('[::1]:6667', '[::1]:19106').replace('":6697":', '"127.0.0.1:19107":')
        (irc / 'ircd.yaml').write_text(config)
        shutil.copytree(PREFIX / 'share/doc/ergo/languages', irc / 'languages')
        run(['ergo', 'mkcerts', '--conf', 'ircd.yaml'], cwd=irc)
        with daemon(['ergo', 'run', '--conf', 'ircd.yaml'], irc) as process:
            wait_port(19106, process)
            with socket.create_connection(('127.0.0.1', 19106), timeout=10) as client:
                client.sendall(b'NICK termuxci\r\nUSER termuxci 0 * :Native CI\r\n')
                data = b''
                while b' 001 termuxci ' not in data:
                    chunk = client.recv(65536); assert chunk, data
                    data += chunk
                    for line in chunk.split(b'\r\n'):
                        if line.startswith(b'PING '): client.sendall(b'PONG ' + line[5:] + b'\r\n')
                client.sendall(b'QUIT :ci complete\r\n')
        print('PASS: Ergo IRC registration receives welcome 001', flush=True)

        database = work / 'native.sqlite3'
        with sqlite3.connect(database) as connection:
            connection.execute('CREATE TABLE native_check (value TEXT)')
            connection.execute('INSERT INTO native_check VALUES ("bionic")')
        tui(['rainfrog', '--url', 'sqlite://' + str(database)], work, 'native_check', b'\x03')
        (work / 'slides.md').write_text('# Native Android slide\n\nHello Termux\n')
        tui(['presenterm', '--image-protocol', 'ascii-blocks', str(work / 'slides.md')], work, 'Hello Termux')
        run(['termscp', 'update'], cwd=work)  # Pacman ownership must survive self-update requests.
        tui(['termscp', '--wno-keyring'], work, 'Protocol', b'\x03')
        jj = work / 'jj'; jj.mkdir()
        run(['jj', 'git', 'init', str(jj)], cwd=work)
        run(['jj', 'config', 'set', '--repo', 'user.name', 'Termux CI'], cwd=jj)
        run(['jj', 'config', 'set', '--repo', 'user.email', 'ci@example.invalid'], cwd=jj)
        tui(['lazyjj'], jj, 'Changes')

    # Vanilla server comes directly from Re-Logic at setup time; it is not in .pkg.tar.xz.
    run(['terraria-server', 'install'], timeout=300)
    vanilla = work / 'vanilla'; vanilla.mkdir()
    world = vanilla / 'ci.wld'
    args = ['terraria-server', 'run', '-lang', '1', '-ip', '127.0.0.1', '-port', '19108', '-noupnp', '-world', str(world), '-autocreate', '1', '-seed', '42', '-maxplayers', '2']
    with daemon(args, vanilla) as process:
        wait_port(19108, process, 240)
        with socket.create_connection(('127.0.0.1', 19108), timeout=10) as client:
            # 1.4.5.8's curRelease is 326. Exercise a valid connection and world
            # info request instead of racing the immediate wrong-version kick.
            message = b'\x01\x0bTerraria326'
            client.sendall(struct.pack('<H', len(message) + 2) + message)
            def packet():
                def exact(size):
                    data = b''
                    while len(data) < size:
                        chunk = client.recv(size - len(data)); assert chunk, data
                        data += chunk
                    return data
                length, = struct.unpack('<H', exact(2))
                assert 3 <= length <= 65535
                return exact(length - 2)
            reply = packet()
            assert reply[0] == 3, reply
            client.sendall(b'\x03\x00\x06')
            reply = packet()
            assert reply[0] == 7 and len(reply) > 20, reply
        process.stdin.write('exit\n'); process.stdin.flush(); process.wait(40)
        assert process.returncode == 0 and world.is_file()
    # Reload the saved world as a distinct process, rather than only checking file creation.
    with daemon(['terraria-server', 'run', '-lang', '1', '-ip', '127.0.0.1', '-port', '19108', '-noupnp', '-world', str(world)], vanilla) as process:
        wait_port(19108, process, 120)
        process.stdin.write('exit\n'); process.stdin.flush(); process.wait(40)
        assert process.returncode == 0 and world.is_file()
    print('PASS: official vanilla native Mono world creation, protocol reply, save and reload', flush=True)

    pumpkin = work / 'pumpkin'; pumpkin.mkdir()
    run(['pumpkin-server', 'install'], timeout=300)
    binary = subprocess.check_output(['pumpkin-server', 'path'], text=True).strip()
    abi = subprocess.check_output(['greadelf', '-h', '-l', '-d', binary], text=True)
    assert 'AArch64' in abi and '/system/bin/linker64' in abi
    assert 'libc.so.6' not in abi and 'ld-linux' not in abi
    print(abi, flush=True)
    (pumpkin / 'pumpkin.toml').write_text('''allow_nether = false
allow_end = false
[networking.java]
address = "127.0.0.1:19110"
view_distance = 2
simulation_distance = 2
[networking.bedrock]
enabled = false
[telemetry]
enabled = false
''')
    with daemon(['pumpkin'], pumpkin) as process:
        wait_port(19110, process, 180)
        with socket.create_connection(('127.0.0.1', 19110), timeout=15) as client:
            # Java status handshake: protocol -1, localhost, requested port, state=status.
            payload = b'\x00\xff\xff\xff\xff\x0f\x09localhost' + struct.pack('>H', 19110) + b'\x01'
            client.sendall(bytes([len(payload)]) + payload + b'\x01\x00')
            def varint():
                value = 0
                for i in range(5):
                    byte = client.recv(1); assert byte
                    value |= (byte[0] & 127) << (7 * i)
                    if byte[0] < 128: return value
                raise AssertionError('bad varint')
            length = varint(); assert varint() == 0
            size = varint(); data = b''
            while len(data) < size:
                chunk = client.recv(size - len(data)); assert chunk
                data += chunk
            status = json.loads(data)
            assert '26.3' in status['version']['name'], status
            print('Pumpkin status:', status['version'], flush=True)
        process.stdin.write('stop\n'); process.stdin.flush(); process.wait(60)
        assert process.returncode == 0
    print('PASS: Pumpkin Android binary Java status protocol and clean stop', flush=True)

print('PASS: all additional package functional smoke tests', flush=True)
