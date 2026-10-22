#!/usr/bin/env python3
"""Transfer real bytes through an authenticated local Chisel tunnel."""
import http.server
import tempfile
import threading
from smoke_support import *

with tempfile.TemporaryDirectory(prefix='chisel-smoke-') as directory:
    work = Path(directory)
    env = environment(work)
    binary = os.environ.get('CHISEL_BIN', 'chisel')
    assert '1.12.0' in run([binary, '--version'], work, env)
    payload = b'chisel-native-payload\n' * 1024
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, *_):
            pass
    origin = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=origin.serve_forever, daemon=True)
    thread.start()
    server_port, local_port = port(), port()
    try:
        with daemon([binary, 'server', '--host', '127.0.0.1', '--port', str(server_port), '--auth', 'smoke:loopback-only'], work, env, 'server') as server:
            ready(server_port, server)
            remote = f'127.0.0.1:{local_port}:127.0.0.1:{origin.server_port}'
            with daemon([binary, 'client', '--auth', 'smoke:loopback-only', f'http://127.0.0.1:{server_port}', remote], work, env, 'client') as client:
                ready(local_port, client)
                with HTTP.open(f'http://127.0.0.1:{local_port}/', timeout=10) as response:
                    assert response.read() == payload
    finally:
        origin.shutdown()
        origin.server_close()
        thread.join(5)
print('PASS chisel: authenticated loopback HTTP payload transfer')
