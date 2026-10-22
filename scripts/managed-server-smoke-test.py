"""Exercise the installed Pacman launcher, direct setup, and persistent worlds."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix='tmodloader-pacman-') as temporary:
    work = Path(temporary)
    env = dict(os.environ, HOME=str(work / 'home'), XDG_DATA_HOME=str(work / 'data'),
               XDG_CONFIG_HOME=str(work / 'config'))
    for key in ('HOME', 'XDG_DATA_HOME', 'XDG_CONFIG_HOME'):
        Path(env[key]).mkdir()
    def run(*args):
        return subprocess.run(args, cwd=work, env=env, text=True, check=True)
    run('tmodloader-server', '--version')
    run('tmodloader-server', 'install')
    installed = Path(subprocess.check_output(['tmodloader-server', 'path'], env=env, text=True).strip())
    marker = json.loads((installed / '.complete.json').read_text())
    assert marker['upstream'] == '2026.08.3.0'
    run('tmodloader-server', 'install')  # The explicit setup is idempotent.
    state = Path(env['XDG_DATA_HOME']) / 'tmodloader-server/state'
    # Upstream creates new worlds under <tmlsavedirectory>/Worlds/<worldname>.
    # First verify that convention, then explicitly load an existing path with
    # spaces. Asking upstream to autocreate at an unrelated filename is not a
    # supported upstream behavior.
    generated = state / 'Worlds/PackageProbe.wld'
    run(sys.executable, '/tests/probe-native-servers-monitor.py', '19203',
        'tmodloader-server', 'run', '-lang', 'en-US', '-ip', '127.0.0.1',
        '-port', '19203', '-world', str(generated), '-worldname', 'PackageProbe',
        '-autocreate', '1', '-maxplayers', '2')
    assert generated.is_file() and generated.stat().st_size > 1000
    world = work / 'world with spaces.wld'
    generated.rename(world)
    modded = generated.with_suffix('.twld')
    assert modded.is_file(), 'No modded world metadata was saved'
    modded.rename(world.with_suffix('.twld'))
    run(sys.executable, '/tests/probe-native-servers-monitor.py', '19203',
        'tmodloader-server', 'run', '-lang', 'en-US', '-ip', '127.0.0.1',
        '-port', '19203', '-world', str(world), '-maxplayers', '2')
    assert world.is_file() and world.stat().st_size > 1000
    assert not list(installed.rglob('*.wld')), 'Save data must remain outside versioned program files'
    assert not generated.exists(), 'Explicit world path was ignored'
    assert state.is_dir()
    print('PASS: tModLoader Pacman launcher, pinned upstream setup, world path with spaces, protocol, save and reload')
