"""Exercise native server startup, protocol, save, and a separate reload."""
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
                    raise RuntimeError('Server exited before listening')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=1) as client:
                        message = b'\x01\x09Terraria0'
                        client.sendall(struct.pack('<H', len(message) + 2) + message)
                        client.settimeout(10)
                        reply = client.recv(4096)
                        assert len(reply) >= 3 and reply[2] == 2, reply
                        break
                except ConnectionRefusedError:
                    time.sleep(1)
            else:
                raise RuntimeError('Server startup timed out')
            process.stdin.write('exit\n'); process.stdin.flush()
            assert process.wait(60) == 0
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(15)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
            log.seek(0)
            print(log.read()[-18000:], flush=True)

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
