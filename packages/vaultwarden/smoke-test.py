#!/usr/bin/env python3
"""Synthetic API/storage/restart test; no real account, vault or remote service."""
import base64
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from smoke_support import HTTP, daemon, environment, port, ready


with tempfile.TemporaryDirectory(prefix='vaultwarden-smoke-') as temporary:
    work = Path(temporary)
    env = environment(work)
    # Never inherit a real deployment's configuration or credentials.
    for key in list(env):
        if key.startswith(('SMTP_', 'SSO_', 'PUSH_', 'YUBICO_', 'DUO_')) or key in (
            'ADMIN_TOKEN', 'DATABASE_URL', 'DATABASE_URL_FILE', 'SIGNUPS_ALLOWED',
            'INVITATIONS_ALLOWED', 'CONFIG_FILE', 'ENV_FILE', 'DATA_FOLDER',
            'ROCKET_TLS', 'WEB_VAULT_FOLDER', 'WEB_VAULT_ENABLED', 'DOMAIN',
        ):
            env.pop(key)
    number = port()
    base = f'http://127.0.0.1:{number}'
    data = work / 'vault-data'
    env.update(DATA_FOLDER=str(data), ROCKET_ADDRESS='127.0.0.1', ROCKET_PORT=str(number),
               DOMAIN=base, ENV_FILE='/dev/null', CONFIG_FILE=str(data / 'config.json'),
               SIGNUPS_VERIFY='false', PUSH_ENABLED='false', DISABLE_ICON_DOWNLOAD='true')
    executable = sys.argv[1] if len(sys.argv) > 1 else 'vaultwarden'
    account = 'termux-ci-only@example.invalid'
    password = base64.b64encode(b'synthetic-auth-hash-not-a-secret!').decode()
    # Vaultwarden treats encrypted fields as opaque. These are only synthetic
    # placeholders, not an assertion that a real client can decrypt this record.
    wrapped = '2.' + '|'.join(base64.b64encode(bytes([x]) * n).decode()
                               for x, n in ((1, 16), (2, 32), (3, 32)))

    def request(path, body=None, token=None, method=None, form=False, expected=200):
        headers = {'Accept': 'application/json', 'Device-Type': '8',
                   'Bitwarden-Client-Version': '2026.9.0'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if body is not None:
            headers['Content-Type'] = ('application/x-www-form-urlencoded' if form else 'application/json')
            body = (urllib.parse.urlencode(body) if form else json.dumps(body)).encode()
        query = urllib.request.Request(base + path, body, headers, method=method)
        try:
            with HTTP.open(query, timeout=20) as response:
                code, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            code, raw = error.code, error.read()
        assert code == expected, (path, code, expected, raw[:800])
        return json.loads(raw) if raw else None

    def login(secret=password, expected=200):
        return request('/identity/connect/token', {
            'grant_type': 'password', 'client_id': 'cli', 'scope': 'api offline_access',
            'username': account, 'password': secret, 'deviceIdentifier': 'termux-ci-device',
            'deviceName': 'Disposable Termux CI', 'deviceType': '8',
        }, form=True, expected=expected)

    with daemon([executable], work, env, 'defaults') as process:
        ready(number, process)
        request('/alive')
        request('/api/config')
        request('/api/sync', expected=401)
        request('/identity/accounts/register/send-verification-email',
                {'email': account, 'name': 'Synthetic CI'}, expected=400)
    print('PASS: Vaultwarden loopback startup, default registration closed, API requires authentication')

    env['SIGNUPS_ALLOWED'] = 'true'
    with daemon([executable], work, env, 'write') as process:
        ready(number, process)
        verification = request('/identity/accounts/register/send-verification-email',
                               {'email': account, 'name': 'Synthetic CI'})
        assert isinstance(verification, str)
        result = request('/identity/accounts/register/finish', {
            'email': account, 'emailVerificationToken': verification,
            'masterPasswordAuthentication': {
                'kdf': {'kdfType': 0, 'iterations': 600000}, 'salt': account,
                'masterPasswordAuthenticationHash': password,
            },
            'masterPasswordUnlock': {
                'kdf': {'kdfType': 0, 'iterations': 600000}, 'salt': account,
                'masterKeyWrappedUserKey': wrapped,
            },
        })
        assert result['object'] == 'registerFinish', result
        login('deliberately-wrong', expected=400)
        session = login()
        token = session['access_token']
        profile = request('/api/accounts/profile', token=token)
        user_id = profile['id']
        assert profile['email'] == account
        payload = {'type': 2, 'name': wrapped, 'notes': wrapped,
                   'secureNote': {'type': 0}, 'encryptedFor': user_id,
                   'favorite': False, 'reprompt': 0}
        cipher = request('/api/ciphers', payload, token)
        cipher_id = cipher['id']
        assert cipher['name'] == wrapped and cipher['notes'] == wrapped
        payload['favorite'] = True
        updated = request('/api/ciphers/' + cipher_id, payload, token, method='PUT')
        assert updated['favorite'] is True
        synced = request('/api/sync', token=token)
        assert any(c['id'] == cipher_id and c['favorite'] for c in synced['ciphers'])
    database = data / 'db.sqlite3'
    assert database.is_file() and database.stat().st_size > 0
    with sqlite3.connect(f'file:{database}?mode=ro', uri=True) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert connection.execute('SELECT count(*) FROM users WHERE email=?', (account,)).fetchone()[0] == 1
        assert connection.execute('SELECT name FROM ciphers WHERE uuid=?', (cipher_id,)).fetchone()[0] == wrapped
    key = data / 'rsa_key.pem'
    assert key.is_file()
    key_before = key.read_bytes()
    print('PASS: synthetic account registration, bad-password rejection, login, cipher create/update/sync, SQLite integrity')

    env['SIGNUPS_ALLOWED'] = 'false'
    with daemon([executable], work, env, 'restart') as process:
        ready(number, process)
        token = login()['access_token']
        persisted = request('/api/ciphers/' + cipher_id, token=token)
        assert persisted['name'] == wrapped and persisted['favorite'] is True
        synced = request('/api/sync', token=token)
        assert any(c['id'] == cipher_id for c in synced['ciphers'])
        request('/api/ciphers/' + cipher_id, token=token, method='DELETE')
        synced = request('/api/sync', token=token)
        assert all(c['id'] != cipher_id for c in synced['ciphers'])
        request('/identity/accounts/register/send-verification-email',
                {'email': 'another-ci@example.invalid'}, expected=400)
    assert key.read_bytes() == key_before
    with sqlite3.connect(f'file:{database}?mode=ro', uri=True) as connection:
        assert connection.execute('SELECT count(*) FROM ciphers WHERE uuid=?', (cipher_id,)).fetchone()[0] == 0
    assert (data.stat().st_mode & 0o077) == 0
    print('PASS: restart preserves synthetic account/cipher and signing key; login, sync, deletion and closed registration')

print('PASS: Vaultwarden synthetic API/storage/restart test; all temporary account data removed')
subprocess.run([sys.executable, str(Path(__file__).with_name('tls-smoke-test.py')), executable],
               check=True, timeout=180)
