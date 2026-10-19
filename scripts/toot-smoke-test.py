#!/usr/bin/env python3
"""Offline checks for the installed package; no accounts or network access."""
import asyncio
from importlib import metadata
import os
from pathlib import Path
import socket
import ssl
import sys
import tempfile

bundle = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(bundle))


def offline(*args, **kwargs):
    raise AssertionError('Network access attempted during offline smoke test')


socket.socket.connect = offline
socket.socket.connect_ex = offline
socket.create_connection = offline
socket.getaddrinfo = offline

with tempfile.TemporaryDirectory(prefix='toot-smoke-') as home:
    os.environ.update(HOME=home, APPDATA=home, XDG_CONFIG_HOME=home)
    from click.testing import CliRunner
    from toot.cli import cli
    import toot

    assert toot.__version__ == '0.52.1', toot.__version__
    for args, expected in [(['--version'], 'v0.52.1'),
                           (['--help'], 'Commands:'),
                           (['tui', '--help'], '--colors')]:
        result = CliRunner().invoke(cli, args)
        assert result.exit_code == 0, (args, result.output, result.exception)
        assert expected in result.output, result.output
    print('PASS: toot version, CLI help, TUI help (offline)')
    if '--cli-only' not in sys.argv:
        import certifi
        import requests
        from toot import App, User
        from toot.tui.app import TUI, TuiOptions
        from toot.tui.images import image_support_enabled

        assert Path(certifi.where()).resolve() == bundle.parents[1] / 'etc/tls/cert.pem'
        assert requests.utils.DEFAULT_CA_BUNDLE_PATH == certifi.where()
        assert ssl.create_default_context(cafile=certifi.where()).cert_store_stats()['x509_ca']
        assert metadata.version('urwid').startswith('3.')
        assert not image_support_enabled()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        options = TuiOptions(16, None, False, False, 0, 'public', 'block', False)
        # Empty dummy credentials are never saved or sent. TUI.run() would load
        # remote data, so exercise construction and rendering without running it.
        tui = TUI.create(App('example.invalid', 'https://example.invalid', '', ''),
                         User('example.invalid', 'offline', ''), options)
        try:
            canvas = tui.render((80, 24), focus=True)
            assert canvas.cols() == 80 and canvas.rows() == 24
            assert b'offline@example.invalid' in b'\n'.join(canvas.text)
        finally:
            tui.executor.shutdown(wait=True)
            loop.close()
            asyncio.set_event_loop(None)
        print('PASS: private dependencies, system CA bundle, TUI construction and 80x24 rendering (offline)')
