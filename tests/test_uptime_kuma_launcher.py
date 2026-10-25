"""Exercise the installed launcher with a tiny Node stand-in, without npm."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_data_directory_stays_outside_package_across_restart(self):
        for setting in ('relative', 'absolute', 'default'):
            with self.subTest(setting=setting), tempfile.TemporaryDirectory() as temporary:
                work = Path(temporary)
                prefix = work / 'usr'
                application = prefix / 'lib/uptime-kuma'
                application.mkdir(parents=True)
                (prefix / 'bin').mkdir()
                home = work / 'home'
                home.mkdir()
                caller = work / 'caller'
                caller.mkdir()
                node = prefix / 'bin/node'
                node.write_text('''#!/usr/bin/env python3
import json, os
from pathlib import Path
data = Path(os.environ['DATA_DIR'])
data.mkdir(parents=True, exist_ok=True)
state = data / 'restart-count'
count = int(state.read_text()) + 1 if state.exists() else 1
state.write_text(str(count))
print(json.dumps({'data': str(data.resolve()), 'count': count, 'cwd': os.getcwd()}))
''')
                node.chmod(0o700)
                launcher = work / 'uptime-kuma'
                launcher.write_text((ROOT / 'packages/uptime-kuma/uptime-kuma').read_text()
                                    .replace('@TERMUX_PREFIX@', str(prefix)))
                env = {**os.environ, 'HOME': str(home)}
                env.pop('XDG_DATA_HOME', None)
                env.pop('DATA_DIR', None)
                expected = home / '.local/share/uptime-kuma'
                if setting != 'default':
                    expected = caller / 'monitor data'
                    env['DATA_DIR'] = 'monitor data' if setting == 'relative' else str(expected)
                for count in (1, 2):
                    result = subprocess.run(['sh', str(launcher)], cwd=caller, env=env,
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout),
                                     {'data': str(expected), 'count': count, 'cwd': str(application)})
                self.assertEqual(list(application.iterdir()), [])
                self.assertEqual(expected.stat().st_mode & 0o077, 0)


if __name__ == '__main__':
    unittest.main()
