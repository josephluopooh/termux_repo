"""Exercise native server startup, protocol, save, and a separate reload."""
import os
import json
import pathlib
import socket
import struct
import subprocess
import sys
import time

port = int(sys.argv[1])
args = sys.argv[2:]

def boot(command, name):
    with open(name + '.log', 'w+') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log,
                                   stderr=subprocess.STDOUT, text=True)
        try:
            end = time.monotonic() + 240
            while time.monotonic() < end:
                if process.poll() is not None:
                    raise RuntimeError('Server exited before listening: ' + str(process.returncode))
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=1) as client:
                        version = os.environ.get('SERVER_PROTOCOL_VERSION', '0')
                        tag = ('Terraria' + version).encode('ascii')
                        message = b'\x01' + bytes([len(tag)]) + tag
                        client.sendall(struct.pack('<H', len(message) + 2) + message)
                        client.settimeout(10)
                        def packet():
                            def exact(size):
                                data = b''
                                while len(data) < size:
                                    chunk = client.recv(size - len(data)); assert chunk, data
                                    data += chunk
                                return data
                            length, = struct.unpack('<H', exact(2))
                            assert 3 <= length <= 65535, length
                            return exact(length - 2)
                        reply = packet()
                        if version == '0':
                            assert reply[0] == 2, reply
                        else:
                            assert reply[0] == 3, reply
                            # TShock keeps its normal UUID requirement; a
                            # synthetic client must supply packet 68 before 6.
                            if identifier := os.environ.get('SERVER_PROTOCOL_UUID'):
                                identifier = identifier.encode('ascii')
                                assert len(identifier) == 36
                                uuid_packet = b'\x44' + bytes([len(identifier)]) + identifier
                                client.sendall(struct.pack('<H',len(uuid_packet)+2)+uuid_packet)
                            client.sendall(b'\x03\x00\x06')
                            reply = packet()
                            assert reply[0] == 7 and len(reply) > 20, reply
                            print('PASS: valid protocol handshake and world info', flush=True)
                        break
                except ConnectionRefusedError:
                    time.sleep(1)
            else:
                raise RuntimeError('Server startup timed out')
            if os.environ.get('SERVER_PROTOCOL_VERSION'):
                # An unsupported client must get a kick without crashing the server.
                with socket.create_connection(('127.0.0.1', port), timeout=10) as invalid:
                    invalid.sendall(b'\x0d\x00\x01\x09Terraria0')
                    reply = invalid.recv(4096)
                    assert len(reply) >= 3 and reply[2] == 2, reply
                time.sleep(1)
                assert process.poll() is None, 'Server crashed after wrong-version packet'
                print('PASS: wrong-version rejection remains stable', flush=True)
            if name == 'native-create':
                for command in json.loads(os.environ.get('SERVER_TEST_CONSOLE_COMMANDS', '[]')):
                    process.stdin.write(command + '\n')
            process.stdin.write('exit\n'); process.stdin.flush()
            assert process.wait(60) == 0
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(15)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
            log.seek(0)
            print(log.read()[-18000:], flush=True)
            if process.returncode:
                for detail in pathlib.Path.cwd().rglob('*.log'):
                    if detail.name != name + '.log':
                        print('SERVER_LOG', detail, detail.read_text(errors='replace')[-5000:], flush=True)

boot(args, 'native-create')
worlds = list(pathlib.Path.cwd().rglob('*.wld'))
print('Saved worlds:', [(str(p), p.stat().st_size) for p in worlds], flush=True)
assert len(worlds) == 1 and worlds[0].stat().st_size > 1000, worlds
world = worlds[0]
reload_args = args.copy()
reload_args[reload_args.index('-world') + 1] = str(world)
for option in ('-autocreate', '-seed'):
    if option in reload_args:
        index = reload_args.index(option)
        del reload_args[index:index + 2]
boot(reload_args, 'native-reload')
assert world.is_file() and world.stat().st_size > 1000
print('NATIVE_SERVER_RESULT: PASS create, protocol reply, save, reload, clean exit', flush=True)
