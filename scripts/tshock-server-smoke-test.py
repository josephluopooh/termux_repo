"""Exercise the actual Pacman TShock launcher and persistent server state."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix='tshock-pacman-') as temporary:
    work = Path(temporary)
    env = dict(os.environ, HOME=str(work/'home'), XDG_DATA_HOME=str(work/'data'),
               XDG_CONFIG_HOME=str(work/'config'), SERVER_PROTOCOL_VERSION='326',
               SERVER_PROTOCOL_UUID='4e07c9d4-82eb-4a74-9cd8-935a3f941f5f',
               SERVER_TEST_CONSOLE_COMMANDS=json.dumps(['group add termux_probe']))
    for key in ('HOME', 'XDG_DATA_HOME', 'XDG_CONFIG_HOME'):
        Path(env[key]).mkdir()
    def run(*args):
        return subprocess.run(args, cwd=work, env=env, text=True, check=True)
    run('tshock-server', '--version')
    run('tshock-server', 'install')
    installed = Path(subprocess.check_output(['tshock-server', 'path'],env=env,text=True).strip())
    marker = json.loads((installed/'.complete.json').read_text())
    assert marker['upstream'] == '6.2.1'
    assert (installed/'licenses/Steamworks.NET-MIT.txt').stat().st_size > 500
    run('tshock-server', 'install')
    world = work/'world with spaces.wld'
    run(sys.executable, '/tests/probe-native-servers-monitor.py', '19203',
        'tshock-server', 'run', '-lang', '1', '-ip', '127.0.0.1', '-port', '19203',
        '-world', str(world), '-worldname', 'TShockProbe', '-autocreate', '1', '-maxplayers', '2')
    assert world.is_file() and world.stat().st_size > 1000
    state = Path(env['XDG_DATA_HOME'])/'tshock-server/state'
    database = state/'tshock/tshock.sqlite'
    assert database.is_file() and (state/'tshock/config.json').is_file()
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as connection:
        tables = {row[0].lower() for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'users','grouplist'} <= tables, tables
        assert connection.execute('SELECT COUNT(*) FROM GroupList WHERE GroupName=?',('termux_probe',)).fetchone()[0] == 1
    assert not list(installed.rglob('*.wld')) and not list(installed.rglob('*.sqlite'))
    assert (state/'ServerPlugins').is_dir()
    print('PASS: TShock Pacman launcher, pinned setup, valid protocol/world info, wrong-version stability, save/reload, persistent SQLite administration and external state')
