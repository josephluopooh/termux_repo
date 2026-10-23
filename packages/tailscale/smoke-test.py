#!/usr/bin/env python3
"""Unauthenticated local Tailscale API, proxy payload and persistent preferences."""
import base64
import http.client
import http.server
import struct
import tempfile
import threading
from smoke_support import *


class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__('local-tailscaled.sock', timeout=10)
        self.path = str(path)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def api(path, resource, method='GET', data=None):
    connection = UnixHTTP(path)
    try:
        body = None if data is None else json.dumps(data)
        connection.request(method, '/localapi/v0/' + resource, body,
                           {'Content-Type': 'application/json'})
        response = connection.getresponse()
        payload = response.read()
        assert response.status == 200, (resource, response.status)
        return json.loads(payload)
    finally:
        connection.close()


def wait_api(path, process):
    end = time.monotonic() + 40
    while time.monotonic() < end:
        assert process.poll() is None, 'Daemon exited before API was ready'
        try:
            status = api(path, 'status')
            if status['BackendState'] in ('NeedsLogin', 'Stopped'):
                return status
        except (OSError, http.client.HTTPException, AssertionError):
            pass
        time.sleep(.2)
    raise AssertionError('Tailscale local API did not reach unauthenticated state')


def exact(connection, size):
    data = b''
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        assert chunk, 'Proxy closed connection early'
        data += chunk
    return data


def socks_transfer(proxy_port, target_port, expected):
    with socket.create_connection(('127.0.0.1', proxy_port), timeout=10) as client:
        client.sendall(b'\x05\x01\x00')
        assert exact(client, 2) == b'\x05\x00'
        client.sendall(b'\x05\x01\x00\x01' + socket.inet_aton('127.0.0.1') + struct.pack('>H', target_port))
        header = exact(client, 4)
        assert header[:3] == b'\x05\x00\x00', header
        address_size = {1: 4, 4: 16}.get(header[3])
        if address_size is None:
            assert header[3] == 3
            address_size = exact(client, 1)[0]
        exact(client, address_size + 2)
        client.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        response = http.client.HTTPResponse(client)
        response.begin()
        assert response.status == 200 and response.read() == expected


with tempfile.TemporaryDirectory(prefix='tailscale-smoke-') as directory:
    work = Path(directory)
    env = environment(work)
    # Prevent inherited Tailscale test/debug settings from affecting this gate.
    env = {k: v for k, v in env.items() if not k.startswith('TS_')}
    env['TS_NO_LOGS_NO_SUPPORT'] = 'true'
    cli = os.environ.get('TAILSCALE_BIN', 'tailscale')
    server = os.environ.get('TAILSCALED_BIN', 'tailscaled')
    assert '1.104.2' in run([cli, 'version'], work, env)
    state = work / 'state'
    state.mkdir(mode=0o700)
    # A fresh unauthenticated profile is intentionally in-memory upstream. Seed
    # a synthetic saved profile with NO login, NodeID, keys or credentials so
    # the real API can exercise the file-backed preference update/reload path.
    # This fixture cannot authenticate to a tailnet.
    profile_key = 'profile-ci01'
    fixture = {
        '_profiles': json.dumps({'ci01': {'ID': 'ci01', 'Key': profile_key,
                                         'Name': 'offline-ci'}}).encode(),
        '_current-profile': profile_key.encode(),
        profile_key: json.dumps({'WantRunning': False, 'LoggedOut': True,
                                 'ControlURL': 'http://127.0.0.1:1',
                                 'CorpDNS': False, 'Config': None}).encode(),
    }
    state_file = state / 'tailscaled.state'
    state_file.write_text(json.dumps({key: base64.b64encode(value).decode()
                                     for key, value in fixture.items()}))
    state_file.chmod(0o600)
    api_path = work / 'daemon.sock'
    socks_port, http_port = port(), port()
    args = [server, '--tun=userspace-networking', '--statedir=' + str(state),
            '--socket=' + str(api_path), '--port=0', '--no-logs-no-support',
            '--socks5-server=127.0.0.1:' + str(socks_port),
            '--outbound-http-proxy-listen=127.0.0.1:' + str(http_port)]
    payload = b'tailscale-local-proxy-payload\n' * 1024

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
    try:
        with daemon(args, work, env, 'daemon') as process:
            initial = wait_api(api_path, process)
            assert initial.get('TailscaleIPs') in (None, []), 'Unexpected authenticated state'
            cli_status = json.loads(run([cli, '--socket=' + str(api_path), 'status', '--json'], work, env))
            assert cli_status['BackendState'] in ('NeedsLogin', 'Stopped')
            ready(socks_port, process)
            ready(http_port, process)
            socks_transfer(socks_port, origin.server_port, payload)
            proxy = http.client.HTTPConnection('127.0.0.1', http_port, timeout=10)
            try:
                proxy.request('GET', 'http://127.0.0.1:' + str(origin.server_port) + '/')
                response = proxy.getresponse()
                assert response.status == 200 and response.read() == payload
            finally:
                proxy.close()
            # Keep WantRunning=false and never invoke login/up. No control-plane
            # account or external authentication is needed to save local prefs.
            preferences = api(api_path, 'prefs', 'PATCH', {
                'Hostname': 'termux-native-smoke', 'HostnameSet': True,
                'WantRunning': False, 'WantRunningSet': True,
                'CorpDNS': False, 'CorpDNSSet': True,
                'ControlURL': 'http://127.0.0.1:1', 'ControlURLSet': True,
            })
            assert preferences['Hostname'] == 'termux-native-smoke'
            assert preferences['WantRunning'] is False
        assert state_file.is_file() and state_file.stat().st_size > 0
        assert state_file.stat().st_mode & 0o077 == 0, 'State must be private'
        saved = json.loads(base64.b64decode(json.loads(state_file.read_text())[profile_key]))
        assert saved['Hostname'] == 'termux-native-smoke', 'Daemon did not persist API change'
        with daemon(args, work, env, 'restart') as process:
            wait_api(api_path, process)
            preferences = api(api_path, 'prefs')
            assert preferences['Hostname'] == 'termux-native-smoke'
            assert preferences['WantRunning'] is False
            assert preferences['ControlURL'] == 'http://127.0.0.1:1'
            ready(socks_port, process)
            socks_transfer(socks_port, origin.server_port, payload)
    finally:
        origin.shutdown()
        origin.server_close()
        thread.join(5)

print('PASS tailscale: unauthenticated CLI/local API, SOCKS5 and HTTP payloads, private preferences survive restart; no tailnet/hardware claim')
