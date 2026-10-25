"""Test retention with genuine signed bytes, without creating signing keys.

The small SHA256SUMS fixture and its signature are from:
https://github.com/josephluopooh/termux_repo/releases/tag/repo-aarch64-39998888329-1
They stand in for large package/source payloads; GPG authenticates bytes, not names.
Policy tests replace only the authenticated manifest mapping, because its signed
hashes describe the original large release files. Manifest authentication itself
is tested separately against the genuine fixture; no signing keys are created.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures'
PACKAGE = 'vaultwarden-1.37.4-1.33.1-aarch64.pkg.tar.xz'
SOURCE = 'vaultwarden-1.37.4-source.tar.gz'
SPEC = importlib.util.spec_from_file_location('retention', ROOT / 'scripts/retain-release.py')
RETENTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETENTION)

POLICY_DRIVER = '''
import importlib.util, json, sys
from pathlib import Path
from unittest import mock
spec = importlib.util.spec_from_file_location('retention', sys.argv[1])
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)
with mock.patch.object(retention, 'load_manifest', return_value=json.loads(sys.argv[4])):
    retention.retain(Path(sys.argv[2]), Path(sys.argv[3]))
'''


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
        self.hashes = {}
        shutil.copyfile(FIXTURES / 'release-SHA256SUMS', self.previous / 'SHA256SUMS')
        shutil.copyfile(FIXTURES / 'release-SHA256SUMS.sig', self.previous / 'SHA256SUMS.sig')
        self.payload(PACKAGE)
        self.payload(SOURCE)

    def payload(self, name):
        shutil.copyfile(FIXTURES / 'release-SHA256SUMS', self.previous / name)
        shutil.copyfile(FIXTURES / 'release-SHA256SUMS.sig', self.previous / (name + '.sig'))
        self.names.extend([name, name + '.sig'])
        for filename in (name, name + '.sig'):
            self.hashes[filename] = hashlib.sha256((self.previous / filename).read_bytes()).hexdigest()

    def retain(self, authenticated=False):
        (self.previous / 'release.json').write_text(json.dumps(
            {'assets': [{'name': name} for name in self.names + ['SHA256SUMS', 'SHA256SUMS.sig']]}))
        args = [str(ROOT / 'scripts/retain-release.py'), str(self.previous), str(self.destination)]
        command = ([sys.executable, *args] if authenticated else
                   [sys.executable, '-c', POLICY_DRIVER, *args, json.dumps(self.hashes)])
        return subprocess.run(command,
                              env=self.env, capture_output=True, text=True, timeout=20)

    def test_genuine_signed_manifest_is_authenticated_and_parsed(self):
        with mock.patch.dict(os.environ, self.env):
            hashes = RETENTION.load_manifest(self.previous)
        self.assertEqual(hashes[SOURCE], 'db6f25293837096869f608fdf8decee45faddb1eedc5aa49c35fce2d5486f74c')
        self.assertEqual(len(hashes), 188)

    def test_tampered_manifest_is_rejected_before_copying(self):
        manifest = self.previous / 'SHA256SUMS'
        manifest.write_bytes(manifest.read_bytes() + b'tampered')
        result = self.retain(authenticated=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BAD signature', result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_missing_manifest_or_signature_is_rejected(self):
        for name in ('SHA256SUMS', 'SHA256SUMS.sig'):
            with self.subTest(name=name):
                original = (self.previous / name).read_bytes()
                (self.previous / name).unlink()
                result = self.retain(authenticated=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Missing previous checksum manifest', result.stderr)
                self.assertEqual(list(self.destination.iterdir()), [])
                (self.previous / name).write_bytes(original)

    def test_authentic_manifest_detects_source_removed_from_release(self):
        self.names = list(RETENTION.parse_manifest((self.previous / 'SHA256SUMS').read_text()))
        for name in (SOURCE, SOURCE + '.sig'):
            self.names.remove(name)
            (self.previous / name).unlink()
        result = self.retain(authenticated=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing release assets', result.stderr)
        self.assertIn(SOURCE, result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

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

    def test_tampered_payloads_and_signatures_are_rejected_before_copying(self):
        for name in (PACKAGE, PACKAGE + '.sig', SOURCE, SOURCE + '.sig'):
            with self.subTest(name=name):
                original = (self.previous / name).read_bytes()
                (self.previous / name).write_bytes(original + b'tampered')
                result = self.retain()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Checksum mismatch', result.stderr)
                self.assertEqual(list(self.destination.iterdir()), [])
                (self.previous / name).write_bytes(original)

    def test_payload_signatures_are_still_verified_after_hashes(self):
        source = self.previous / SOURCE
        source.write_bytes(source.read_bytes() + b'tampered')
        self.hashes[SOURCE] = hashlib.sha256(source.read_bytes()).hexdigest()
        result = self.retain()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BAD signature', result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

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
        self.assertIn('Missing release assets', result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_payload_removed_from_release_metadata_is_rejected(self):
        for payload in (PACKAGE, SOURCE):
            with self.subTest(payload=payload):
                original = self.names[:]
                self.names.remove(payload)
                self.names.remove(payload + '.sig')
                result = self.retain()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Missing release assets', result.stderr)
                self.assertEqual(list(self.destination.iterdir()), [])
                self.names = original

    def test_unmanifested_payload_is_rejected(self):
        self.names.extend(['extra-source.tar.gz', 'extra-source.tar.gz.sig'])
        result = self.retain()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unmanifested release assets', result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_manifest_requires_payload_signature_entries(self):
        del self.hashes[SOURCE + '.sig']
        result = self.retain()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing checksum manifest signature', result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_legacy_release_without_sources_remains_compatible(self):
        self.names = [PACKAGE, PACKAGE + '.sig']
        self.hashes = {name: self.hashes[name] for name in self.names}
        result = self.retain()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({path.name for path in self.destination.iterdir()}, set(self.names))

    def test_invalid_asset_path_is_rejected(self):
        self.names.extend(['../bad-source.tar.gz', '../bad-source.tar.gz.sig'])
        result = self.retain()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid release asset name', result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])


class ManifestParsingTests(unittest.TestCase):
    def test_rejects_ambiguous_or_unsafe_manifest_entries(self):
        digest = '0' * 64
        for text in ('', f'{digest}  ../package.pkg.tar.xz\n',
                     f'{digest}  /absolute.pkg.tar.xz\n', f'{digest}  ..\n',
                     f'{digest}  bad\\name.pkg.tar.xz\n', f'{digest}  bad\x00name\n',
                     f'{digest} *package.pkg.tar.xz\n', 'invalid  package.pkg.tar.xz\n',
                     f'{digest}  package.pkg.tar.xz\n{digest}  package.pkg.tar.xz\n'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    RETENTION.parse_manifest(text)


if __name__ == '__main__':
    unittest.main()
