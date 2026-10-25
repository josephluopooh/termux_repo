"""Test retention with genuine signed bytes, without creating signing keys.

The small SHA256SUMS fixture and its signature are from:
https://github.com/josephluopooh/termux_repo/releases/tag/repo-aarch64-39998888329-1
They stand in for large package/source payloads; GPG authenticates bytes, not names.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures'
PACKAGE = 'vaultwarden-1.37.4-1.33.1-aarch64.pkg.tar.xz'
SOURCE = 'vaultwarden-1.37.4-source.tar.gz'


class RetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keyring = tempfile.TemporaryDirectory()
        cls.env = {**os.environ, 'GNUPGHOME': cls.keyring.name}
        subprocess.run(['gpg', '--batch', '--import', str(FIXTURES / 'release-public-key.asc')],
                       env=cls.env, check=True, capture_output=True, timeout=10)

    @classmethod
    def tearDownClass(cls):
        subprocess.run(['gpgconf', '--kill', 'gpg-agent'], env=cls.env, check=True, timeout=10)
        cls.keyring.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.previous = self.work / 'previous'
        self.destination = self.work / 'dist'
        self.previous.mkdir()
        self.destination.mkdir()
        self.names = []
        self.payload(PACKAGE)
        self.payload(SOURCE)

    def payload(self, name):
        shutil.copyfile(FIXTURES / 'release-SHA256SUMS', self.previous / name)
        shutil.copyfile(FIXTURES / 'release-SHA256SUMS.sig', self.previous / (name + '.sig'))
        self.names.extend([name, name + '.sig'])

    def retain(self):
        (self.previous / 'release.json').write_text(json.dumps(
            {'assets': [{'name': name} for name in self.names]}))
        return subprocess.run([sys.executable, str(ROOT / 'scripts/retain-release.py'),
                               str(self.previous), str(self.destination)],
                              env=self.env, capture_output=True, text=True, timeout=20)

    def test_preserves_old_packages_sources_and_signatures(self):
        self.payload('adguardhome-0.107.79-1.34.1-source.tar.gz')
        new_source = self.destination / 'vaultwarden-1.37.4-1.34.1-source.tar.gz'
        new_source.write_bytes(b'new revision corresponding source')
        result = self.retain()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in self.names:
            self.assertEqual((self.destination / name).read_bytes(),
                             (self.previous / name).read_bytes())
        self.assertEqual(new_source.read_bytes(), b'new revision corresponding source')

    def test_equal_collision_keeps_current_signature(self):
        shutil.copyfile(self.previous / SOURCE, self.destination / SOURCE)
        signature = self.destination / (SOURCE + '.sig')
        shutil.copyfile(self.previous / (SOURCE + '.sig'), signature)
        os.utime(signature, (1000, 1000))
        result = self.retain()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(signature.read_bytes(), (self.previous / (SOURCE + '.sig')).read_bytes())
        self.assertEqual(signature.stat().st_mtime, 1000)

    def test_different_bytes_under_same_name_fail_before_copying(self):
        (self.destination / SOURCE).write_bytes(b'different source for the same version')
        result = self.retain()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.destination.iterdir()), [self.destination / SOURCE])
        self.assertEqual((self.destination / SOURCE).read_bytes(), b'different source for the same version')

    def test_tampered_payloads_are_rejected_before_copying(self):
        for name in (PACKAGE, SOURCE):
            with self.subTest(name=name):
                original = (self.previous / name).read_bytes()
                (self.previous / name).write_bytes(original + b'tampered')
                result = self.retain()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('BAD signature', result.stderr)
                self.assertEqual(list(self.destination.iterdir()), [])
                (self.previous / name).write_bytes(original)

    def test_missing_downloads_are_not_silently_skipped(self):
        for name in (PACKAGE, SOURCE, SOURCE + '.sig'):
            with self.subTest(name=name):
                original = (self.previous / name).read_bytes()
                (self.previous / name).unlink()
                result = self.retain()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Missing downloaded asset', result.stderr)
                self.assertEqual(list(self.destination.iterdir()), [])
                (self.previous / name).write_bytes(original)

    def test_unsigned_source_in_release_is_rejected(self):
        self.names.remove(SOURCE + '.sig')
        result = self.retain()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing release signature', result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_legacy_release_without_sources_remains_compatible(self):
        self.names = [PACKAGE, PACKAGE + '.sig']
        result = self.retain()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({path.name for path in self.destination.iterdir()}, set(self.names))

    def test_invalid_asset_path_is_rejected(self):
        self.names.extend(['../bad-source.tar.gz', '../bad-source.tar.gz.sig'])
        result = self.retain()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid release asset name', result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
