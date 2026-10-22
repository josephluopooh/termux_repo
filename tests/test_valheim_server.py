"""Network-free launcher tests. These do not run .NET, Box64, or Valheim."""
from contextlib import nullcontext
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / 'packages/valheim-server/valheim-server'
spec = importlib.util.spec_from_loader('valheim_launcher', importlib.machinery.SourceFileLoader('valheim_launcher', str(SOURCE)))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def fake_payload(folder):
    folder.mkdir(parents=True, exist_ok=True)
    header = bytearray(64)
    header[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', header, 18, 62)
    (folder / 'valheim_server.x86_64').write_bytes(header)
    (folder / 'UnityPlayer.so').write_bytes(header)
    (folder / 'valheim_server_Data').mkdir(exist_ok=True)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='valheim test ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'XDG_DATA_HOME': str(self.root / 'data'),
                                          'XDG_CONFIG_HOME': str(self.root / 'config')})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.paths = app.Paths()
        self.config = dict(name='My server; $(false)', world='My World', password='a "quoted" secret',
                           port=2456, public=False, crossplay=False)

    def install_old(self):
        generation = 'gen-0123456789abcdef'
        fake_payload(self.paths.data / generation)
        app.write_json(self.paths.current, {'generation': generation})
        self.paths.worlds.mkdir()
        (self.paths.worlds / 'world.db').write_bytes(b'precious world')
        app.write_json(self.paths.config, self.config)
        return self.paths.data / generation

    def test_launch_preserves_arguments_and_no_shell(self):
        folder = self.install_old()
        cmd, env = app.launch_command(self.paths, folder, self.config, self.paths.logs / 'log.txt')
        self.assertEqual(cmd[0], str(app.PREFIX / 'glibc/lib/ld.so'))
        self.assertEqual(cmd[3], str(app.PREFIX / 'glibc/bin/box64'))
        self.assertEqual(cmd[cmd.index('-name') + 1], self.config['name'])
        self.assertEqual(cmd[cmd.index('-password') + 1], self.config['password'])
        self.assertEqual(cmd[cmd.index('-savedir') + 1], str(self.paths.worlds))
        self.assertEqual(cmd[cmd.index('-public') + 1], '0')
        self.assertNotIn('-crossplay', cmd)
        self.assertEqual(env['SteamAppId'], '892970')
        self.assertNotIn('proot', ' '.join(cmd))

    def test_native_environment_does_not_mix_glibc_and_android(self):
        with patch.dict(os.environ, {'LD_PRELOAD': 'bionic.so', 'LD_LIBRARY_PATH': '/wrong',
                                     'DOTNET_ROOT': '/wrong', 'DOTNET_ROOT_ARM64': '/wrong'}):
            env = app.native_environment()
            for k in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'DOTNET_ROOT', 'DOTNET_ROOT_ARM64'):
                self.assertNotIn(k, env)
            self.assertEqual(os.environ['LD_PRELOAD'], 'bionic.so')

    def test_config_rejects_crossplay_bad_port_and_traversal(self):
        for key, val in [('crossplay', True), ('public', 1), ('port', True), ('port', 65535),
                         ('port', 1023), ('world', '../bad'), ('world', '..'), ('password', 'abc'),
                         ('name', 'bad\nname'), ('password', self.config['world'])]:
            with self.subTest(key=key, value=val), self.assertRaises(app.Error):
                app.validate_config({**self.config, key: val})
        self.assertEqual(app.validate_config(self.config), self.config)

    def test_download_notice_does_not_invent_an_acceptance_gate(self):
        with patch.object(app.sys.stdin, 'isatty', return_value=False), \
                patch('builtins.input', side_effect=AssertionError('No invented agreement prompt')), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            app.download_notice()
        self.assertIn(app.EULA, output.getvalue())
        self.assertIn(app.STEAM_TERMS, output.getvalue())

    def test_missing_runtime_never_downloads(self):
        app.write_json(self.paths.config, self.config)
        with patch.object(app, 'require_runtime', side_effect=app.Error('Missing runtime')), \
                patch.object(app, 'locked', return_value=nullcontext()), \
                patch.object(app, 'downloader') as download, self.assertRaises(app.Error):
            app.setup(self.paths)
        download.assert_not_called()
        self.assertFalse(self.paths.current.exists())

    def test_checksum_mismatch_rejected(self):
        with patch.object(app.urllib.request, 'urlopen', return_value=io.BytesIO(b'bad')), self.assertRaises(app.Error):
            app.download_verified('https://example.invalid/file', self.root / 'a.zip', '0' * 64)

    def test_archive_traversal_and_symlinks_rejected(self):
        for filename in ('../outside', '/absolute', 'C:/drive', 'a\\b'):
            archive = self.root / 'archive.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr(filename, b'data')
            with self.subTest(filename=filename), self.assertRaises(app.Error):
                app.extract_downloader(archive, self.root / 'out')
        with zipfile.ZipFile(archive, 'w') as z:
            item = zipfile.ZipInfo('link')
            item.external_attr = 0o120777 << 16
            z.writestr(item, '../outside')
        with self.assertRaises(app.Error):
            app.extract_downloader(archive, self.root / 'out')

    def test_pinned_framework_archive_shape(self):
        archive = self.root / 'archive.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('DepotDownloader.runtimeconfig.json', json.dumps({'runtimeOptions': {'tfm': 'net9.0'}}))
            z.writestr('DepotDownloader.dll', b'managed placeholder')
        app.extract_downloader(archive, self.root / 'out')
        self.assertTrue((self.root / 'out/DepotDownloader.dll').is_file())

    def test_wrong_arch_or_incomplete_payload_rejected(self):
        folder = self.root / 'payload'
        fake_payload(folder)
        app.check_payload(folder)
        (folder / 'UnityPlayer.so').write_bytes(b'not an ELF')
        with self.assertRaises(app.Error): app.check_payload(folder)
        (folder / 'UnityPlayer.so').unlink()
        with self.assertRaises(app.Error): app.check_payload(folder)

    def test_active_pointer_cannot_escape_data(self):
        app.write_json(self.paths.current, {'generation': '../../outside'})
        with self.assertRaises(app.Error): app.active(self.paths)

    def test_existing_setup_does_not_download_or_replace_config(self):
        folder = self.install_old()
        before = self.paths.config.read_bytes()
        with patch.object(app, 'require_runtime'), patch.object(app, 'locked', return_value=nullcontext()), \
                patch.object(app, 'downloader') as download, patch.object(app, 'download_notice') as notice:
            app.setup(self.paths)
        download.assert_not_called()
        notice.assert_not_called()
        self.assertEqual(self.paths.config.read_bytes(), before)
        self.assertEqual(app.active(self.paths), folder)

    def run_update(self, callback):
        with patch.object(app, 'require_runtime'), patch.object(app, 'locked', return_value=nullcontext()), \
                patch.object(app, 'download_notice'), patch.object(app, 'downloader', return_value=self.root / 'dummy.zip'), \
                patch.object(app, 'extract_downloader', side_effect=lambda _a, dest: dest.mkdir()), \
                patch.object(app.subprocess, 'run', side_effect=callback):
            app.setup(self.paths, update=True)

    def test_failed_update_preserves_payload_world_and_config(self):
        folder = self.install_old()
        before = self.paths.current.read_bytes(), self.paths.config.read_bytes()
        with self.assertRaises(app.Error):
            self.run_update(lambda *args, **kw: subprocess.CompletedProcess(args[0], 17))
        self.assertEqual(app.active(self.paths), folder)
        self.assertEqual(before, (self.paths.current.read_bytes(), self.paths.config.read_bytes()))
        self.assertEqual((self.paths.worlds / 'world.db').read_bytes(), b'precious world')
        self.assertFalse(list(self.paths.data.glob('.stage-*')))

    def test_successful_update_uses_anonymous_linux64_and_atomic_pointer(self):
        old = self.install_old()
        def run(command, **kw):
            self.assertEqual(command[2:8], ['-app', '896660', '-os', 'linux', '-osarch', '64'])
            self.assertNotIn('-username', command)
            self.assertNotIn('-password', command)
            self.assertEqual(command[-1], '-validate')
            self.assertNotIn('input', kw)
            self.assertNotIn('stdin', kw)
            fake_payload(Path(command[command.index('-dir') + 1]))
            return subprocess.CompletedProcess(command, 0)
        self.run_update(run)
        self.assertNotEqual(app.active(self.paths), old)
        self.assertTrue(old.is_dir())
        self.assertEqual(app.load_json(self.paths.current)['previous_generation'], old.name)
        self.assertEqual((self.paths.worlds / 'world.db').read_bytes(), b'precious world')
        self.assertEqual(app.load_json(self.paths.config), self.config)

    def test_missing_runtime_reports_full_upgrade_and_no_install(self):
        with patch.object(app, 'check_platform'), patch.object(Path, 'is_file', return_value=True), \
                patch.object(app.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'box64-glibc missing')) as run:
            with self.assertRaisesRegex(app.Error, 'pacman -Syu'):
                app.require_runtime()
            self.assertEqual(run.call_args.args[0][1], '-Q')

    def test_atomic_json_failure_does_not_damage_old_file(self):
        path = self.root / 'state.json'
        app.write_json(path, {'old': True})
        with patch.object(app.os, 'replace', side_effect=OSError('disk error')), self.assertRaises(OSError):
            app.write_json(path, {'new': True})
        self.assertEqual(app.load_json(path), {'old': True})
        self.assertEqual(list(self.root.glob('.write-*')), [])

    def test_older_box64_is_rejected(self):
        results = [subprocess.CompletedProcess([], 0, 'box64-glibc 0.4.2', ''),
                   subprocess.CompletedProcess([], 127, 'box64-glibc>=0.4.4', '')]
        with patch.object(app, 'check_platform'), patch.object(Path, 'is_file', return_value=True), \
                patch.object(app.subprocess, 'run', side_effect=results):
            with self.assertRaisesRegex(app.Error, 'version requirements'):
                app.require_runtime()

    def test_supervisor_holds_foreground_and_uses_separate_signal_group(self):
        with patch.object(app.subprocess, 'Popen') as popen:
            popen.return_value.wait.return_value = 0
            self.assertEqual(app.supervise(['fake-box64'], {}, self.root), 0)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])
            popen.return_value.wait.assert_called_once()

    @unittest.skipUnless(os.name == 'posix', 'Real flock needs a POSIX host')
    def test_lock_blocks_concurrent_operation(self):
        with app.locked(self.paths):
            with self.assertRaises(app.Error):
                with app.locked(self.paths):
                    self.fail('Lock unexpectedly acquired')
        with app.locked(self.paths): pass


if __name__ == '__main__':
    unittest.main()
