#!/usr/bin/env python3
"""Exercise outbound TLS against disposable loopback OIDC metadata only.

There is no account login, token exchange, external service or persistent key.
The success case checks the real HTTP client's certificate validation, while
the failure cases prove that untrusted roots and hostname mismatches fail.
"""
import http.server
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

from smoke_support import daemon, environment, port, ready


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
executable = sys.argv[1] if len(sys.argv) > 1 else 'vaultwarden'

with tempfile.TemporaryDirectory(prefix='vaultwarden-tls-smoke-') as temporary:
    work = Path(temporary)
    (work / 'empty-cert-dir').mkdir()
    for name in ('root', 'rogue-root'):
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(work / (name + '.key')), '-out', str(work / (name + '.pem')),
                        '-days', '1', '-subj', '/CN=Disposable CI ' + name,
                        '-addext', 'basicConstraints=critical,CA:TRUE',
                        '-addext', 'keyUsage=critical,keyCertSign,cRLSign'],
                       check=True, timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for name, subject in [('trusted', 'IP:127.0.0.1'), ('wrong-name', 'DNS:ci-only.invalid'),
                          ('untrusted', 'IP:127.0.0.1')]:
        subprocess.run(['openssl', 'req', '-new', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(work / (name + '.key')), '-out', str(work / (name + '.csr')),
                        '-subj', '/CN=Disposable CI ' + name],
                       check=True, timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        extensions = work / (name + '.ext')
        extensions.write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\n'
                              'extendedKeyUsage=serverAuth\nsubjectAltName=' + subject + '\n')
        ca = 'rogue-root' if name == 'untrusted' else 'root'
        subprocess.run(['openssl', 'x509', '-req', '-in', str(work / (name + '.csr')),
                        '-CA', str(work / (ca + '.pem')), '-CAkey', str(work / (ca + '.key')),
                        '-set_serial', str({'trusted': 1, 'wrong-name': 2, 'untrusted': 3}[name]),
                        '-days', '1', '-extfile', str(extensions), '-out', str(work / (name + '.pem'))],
                       check=True, timeout=30, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    roots = work / 'test-roots.pem'
    roots.write_bytes((work / 'root.pem').read_bytes())

    for name in ('trusted', 'untrusted', 'wrong-name'):
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                if self.path == '/.well-known/openid-configuration':
                    value = {'issuer': issuer, 'authorization_endpoint': issuer + '/authorize',
                             'token_endpoint': issuer + '/token', 'userinfo_endpoint': issuer + '/userinfo',
                             'jwks_uri': issuer + '/jwks', 'response_types_supported': ['code'],
                             'subject_types_supported': ['public'], 'id_token_signing_alg_values_supported': ['RS256']}
                elif self.path == '/jwks':
                    value = {'keys': []}
                else:
                    self.send_error(404)
                    return
                content = json.dumps(value).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        issuer = f'https://127.0.0.1:{server.server_port}'
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(work / (name + '.pem')), str(work / (name + '.key')))
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        case = work / name
        case.mkdir()
        env = environment(case)
        for key in list(env):
            if key.endswith('_PROXY') or key.endswith('_proxy') or key.startswith(('SMTP_', 'SSO_', 'PUSH_')):
                env.pop(key)
        number = port()
        base = f'http://127.0.0.1:{number}'
        env.update(DATA_FOLDER=str(case / 'data'), CONFIG_FILE=str(case / 'data/config.json'),
                   ENV_FILE='/dev/null', DATABASE_URL='sqlite://' + str(case / 'data/db.sqlite3'),
                   ROCKET_ADDRESS='127.0.0.1', ROCKET_PORT=str(number), DOMAIN=base,
                   SIGNUPS_ALLOWED='false', WEB_VAULT_ENABLED='false', PUSH_ENABLED='false',
                   SSO_ENABLED='true', SSO_CLIENT_ID='synthetic-ci-client',
                   SSO_CLIENT_SECRET='synthetic-not-a-secret', SSO_AUTHORITY=issuer,
                   SSL_CERT_FILE=str(roots), SSL_CERT_DIR=str(work / 'empty-cert-dir'))
        query = urllib.parse.urlencode({'client_id': 'web', 'redirect_uri': base + '/sso-connector.html',
                                       'state': 'synthetic-ci-state', 'code_challenge': 'A' * 43,
                                       'code_challenge_method': 'S256', 'response_type': 'code'})
        try:
            with daemon([executable], case, env, 'tls-' + name) as process:
                ready(number, process)
                try:
                    response = HTTP.open(base + '/identity/connect/authorize?' + query, timeout=25)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    status, body = response.status, response.read()
                    if name == 'trusted':
                        assert status == 307, (status, body[:800])
                        assert response.headers['Location'].startswith(issuer + '/authorize?')
                        assert '/.well-known/openid-configuration' in requests and '/jwks' in requests, requests
                    else:
                        assert status == 400, (status, body[:800])
                        assert not requests, 'A rejected certificate reached the HTTP handler'
                        assert b'Failed to discover OpenID provider' in body, body[:800]
                with HTTP.open(base + '/alive', timeout=10) as response:
                    assert response.status == 200
                assert process.poll() is None
            print('PASS: Vaultwarden outbound TLS', name,
                  '(metadata accepted)' if name == 'trusted' else '(certificate rejected before HTTP)')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)

print('PASS: outbound TLS trust/hostname verification; synthetic metadata only, temporary keys removed')
