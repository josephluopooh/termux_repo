#!/usr/bin/env python3
"""Offline rootless DNS, bundled dashboard, API and persistent configuration."""
import re
import socketserver
import struct
import tempfile
import threading
from smoke_support import *

class Upstream(socketserver.BaseRequestHandler):
    def handle(self):
        packet, sock = self.request
        # Synthetic authoritative A response; never forwards a packet.
        answer = packet[:2] + struct.pack('!5H', 0x8180, 1, 1, 0, 0) + packet[12:]
        answer += b'\xc0\x0c' + struct.pack('!HHIH', 1, 1, 60, 4) + socket.inet_aton('192.0.2.80')
        sock.sendto(answer, self.client_address)
        self.server.queries += 1

def query(number, name, tcp=False):
    wire = b''.join(bytes([len(label)]) + label.encode() for label in name.split('.')) + b'\x00'
    packet = struct.pack('!6H', 0xABCD, 0x100, 1, 0, 0, 0) + wire + struct.pack('!HH', 1, 1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM) as client:
        client.settimeout(10)
        client.connect(('127.0.0.1', number))
        if tcp:
            client.sendall(struct.pack('!H', len(packet)) + packet)
            def exact(size):
                result = b''
                while len(result) < size:
                    chunk = client.recv(size - len(result)); assert chunk
                    result += chunk
                return result
            response = exact(struct.unpack('!H', exact(2))[0])
        else:
            client.send(packet)
            response = client.recv(4096)
    ident, flags, questions, answers, _, _ = struct.unpack('!6H', response[:12])
    assert ident == 0xABCD and flags & 0x8000 and flags & 15 == 0, response
    assert questions == 1 and answers == 1, response
    return socket.inet_ntoa(response[-4:])

with tempfile.TemporaryDirectory(prefix='adguardhome-smoke-') as directory:
    work = Path(directory)
    env = environment(work)
    env['ADGUARDHOME_WORK_DIR'] = str(work)
    number, dns = port(), port()
    base = f'http://127.0.0.1:{number}'
    binary = os.environ.get('ADGUARDHOME_BIN', 'adguardhome')
    config = work / 'AdGuardHome.yaml'
    template = Path(__file__).with_name('AdGuardHome.yaml').read_text()
    upstream = socketserver.ThreadingUDPServer(('127.0.0.1', 0), Upstream)
    upstream.queries = 0
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    template = template.replace('127.0.0.1:3000', f'127.0.0.1:{number}')
    template = template.replace('port: 5353', f'port: {dns}')
    template = template.replace('127.0.0.1:9', '127.0.0.1:' + str(upstream.server_address[1]))
    config.write_text(template)
    # Direct executable override is for host preflight only. CI uses the installed launcher.
    args = [binary]
    if os.environ.get('ADGUARDHOME_BIN'):
        args += ['--no-check-update', '--no-etc-hosts', '--work-dir', str(work), '--config', str(config)]
    assert 'v0.107.79' in run(args + ['--version'], work, env)
    run(args + ['--check-config'], work, env)
    def api(route, data=None):
        body = None if data is None else json.dumps(data).encode()
        request = urllib.request.Request(base + '/control/' + route, body, {'Content-Type': 'application/json'})
        with HTTP.open(request, timeout=10) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    try:
        with daemon(args, work, env, 'server') as process:
            ready(number, process)
            ready(dns, process)
            status = api('status')
            assert status['running'] and status['dns_port'] == dns, status
            assert status['dns_addresses'] == [f'127.0.0.1:{dns}'], status
            html = HTTP.open(base + '/', timeout=10).read().decode()
            scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
            assert scripts, html[:1000]
            for script in scripts:
                content = HTTP.open(base + '/' + script.lstrip('/'), timeout=10).read()
                assert len(content) > 1000, script
            assert query(dns, 'allowed.example.test') == '192.0.2.80'
            assert upstream.queries > 0
            api('filtering/set_rules', {'rules': ['||blocked.example.test^']})
            assert query(dns, 'blocked.example.test') == '0.0.0.0'
            api('rewrite/add', {'domain': 'stored.example.test', 'answer': '198.51.100.24'})
            assert query(dns, 'stored.example.test', tcp=True) == '198.51.100.24'
            assert '||blocked.example.test^' in api('filtering/status')['user_rules']
        persisted = config.read_text()
        assert 'blocked.example.test' in persisted and 'stored.example.test' in persisted
        assert (work / 'data').is_dir()
        with daemon(args, work, env, 'restart') as process:
            ready(number, process)
            ready(dns, process)
            assert query(dns, 'blocked.example.test', tcp=True) == '0.0.0.0'
            assert query(dns, 'stored.example.test') == '198.51.100.24'
            assert query(dns, 'allowed-after-restart.example.test') == '192.0.2.80'
            assert {'domain': 'stored.example.test', 'answer': '198.51.100.24', 'enabled': True} in api('rewrite/list')
            entries = api('querylog?search=allowed.example.test')['data']
            assert any(e['question']['name'] == 'allowed.example.test' for e in entries), entries
            assert api('stats')['num_dns_queries'] >= 3
    finally:
        upstream.shutdown()
        upstream.server_close()
        thread.join(5)
print('PASS adguardhome: bundled dashboard assets, API, rootless UDP/TCP DNS forwarding/filtering, rules/rewrites/query log/statistics survive restart')
