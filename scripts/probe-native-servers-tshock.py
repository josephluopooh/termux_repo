"""Verify TShock plugin/database state as well as the native game protocol."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

support=Path(sys.argv[1])
setup=support/'managed_setup.py'
installed=Path(subprocess.check_output([sys.executable,str(setup),'tshock','path'],text=True).strip())
work=Path.cwd()
world=work/'world with spaces.wld'
env=dict(os.environ,SERVER_PROTOCOL_VERSION='326',SERVER_PROTOCOL_UUID='4e07c9d4-82eb-4a74-9cd8-935a3f941f5f',SERVER_TEST_CONSOLE_COMMANDS=json.dumps(['group add termux_probe']))
subprocess.run([sys.executable,'/tests/probe-native-servers-monitor.py','19203',
    sys.executable,str(setup),'tshock','run','-lang','1','-ip','127.0.0.1','-port','19203',
    '-world',str(world),'-worldname','TShockProbe','-autocreate','1','-maxplayers','2'],env=env,check=True)
assert world.is_file() and world.stat().st_size>1000
state=Path(os.environ['XDG_DATA_HOME'])/'tshock-server/state'
database=state/'tshock/tshock.sqlite'
assert database.is_file() and (state/'tshock/config.json').is_file(), 'TShock plugin state missing'
with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as connection:
    tables={row[0].lower() for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'users','grouplist'}<=tables,tables
    assert connection.execute('SELECT COUNT(*) FROM GroupList WHERE GroupName=?',('termux_probe',)).fetchone()[0]==1
assert not list(installed.rglob('*.wld')) and not list(installed.rglob('*.sqlite')), 'Mutable world/database is under versioned installation'
assert (state/'ServerPlugins').is_dir()
print('PASS: TShock native protocol, wrong-version stability, saved world, persistent SQLite administration command and external state')
