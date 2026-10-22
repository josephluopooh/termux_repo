"""Retain actual notices for the six pinned, redistributed NuGet dependencies.

Run on the build host. No runtime download or installation hooks are involved.
NuGet's generic MIT URL omits the authors' copyright notices, so obtain the
missing texts from independently pinned upstream source revisions instead.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET

MONOMOD_REVISION = '1fea03f95352a70268a069e68b232c8be0c7f296'
BACKPORTS_REVISION = 'a1b82852b2574742776af08818487b90b0bfab93'
CECIL_REVISION = '5de7d8cbc91f6fd98dcc24b26b8c398db497809c'  # tag 0.11.6
MONOMOD_LICENSE_HASH = '0b64833222e3c6a426ad29362d26334619fe02eaf2b89ea9c37805521896c920'
CECIL_LICENSE_HASH = '13d58ecbed676511c0c4c4009bff107025e50007ff5e7901dc562700ec62509e'
EXPECTED = {
    'mono.cecil/0.11.6': ('jbevain/cecil', CECIL_REVISION, 'LICENSE.txt', CECIL_LICENSE_HASH),
    'monomod.core/1.3.2': ('MonoMod/MonoMod', MONOMOD_REVISION, 'LICENSE', MONOMOD_LICENSE_HASH),
    'monomod.runtimedetour/25.3.2': ('MonoMod/MonoMod', MONOMOD_REVISION, 'LICENSE', MONOMOD_LICENSE_HASH),
    'monomod.utils/25.0.10': ('MonoMod/MonoMod', MONOMOD_REVISION, 'LICENSE', MONOMOD_LICENSE_HASH),
    'monomod.backports/1.1.2': ('MonoMod/MonoMod', BACKPORTS_REVISION, 'LICENSE', MONOMOD_LICENSE_HASH),
    'monomod.ilhelpers/1.1.0': ('MonoMod/MonoMod', BACKPORTS_REVISION, 'LICENSE', MONOMOD_LICENSE_HASH),
}
NOTICE = re.compile(r'^(license|licence|notice|copying|copyright|thirdpartynotices)([._-]|$)', re.I)


def collect(root, dependencies, out):
    libraries = json.loads(dependencies.read_text(encoding='utf-8'))['libraries']
    published = {key.lower(): value for key, value in libraries.items() if value['type'] == 'package'}
    # A new or changed dependency needs an explicit notice audit.
    assert set(published) == set(EXPECTED), (sorted(published), sorted(EXPECTED))
    records, fetched = [], {}
    for identity in sorted(published):
        name, version = identity.split('/')
        directory = root / name / version
        specs = list(directory.glob('*.nuspec'))
        assert len(specs) == 1, (identity, specs)
        spec = specs[0]
        metadata = ET.parse(spec).getroot()
        entries = {e.tag.split('}')[-1]: e.text for e in metadata.iter()}
        assert entries['id'].lower() == name and entries['version'] == version, identity
        archive = directory / f'{name}.{version}.nupkg'
        digest = hashlib.sha512(archive.read_bytes()).digest()
        sha512 = base64.b64encode(digest).decode('ascii')
        expected_digest = published[identity].get('sha512', '').removeprefix('sha512-')
        assert expected_digest and sha512 == expected_digest, (identity, 'NuGet content hash mismatch')
        target = out / identity
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec, target / spec.name)
        notices = []
        for path in sorted(directory.rglob('*')):
            if path.is_file() and NOTICE.match(path.name):
                relative = path.relative_to(directory)
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                notices.append({'path': relative.as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        repository, revision, filename, expected_hash = EXPECTED[identity]
        repo_metadata = next((e for e in metadata.iter() if e.tag.split('}')[-1] == 'repository'), None)
        if repo_metadata is not None:
            assert repo_metadata.attrib.get('commit') == revision, identity
        url = f'https://raw.githubusercontent.com/{repository}/{revision}/{filename}'
        if url not in fetched:
            request = urllib.request.Request(url, headers={'User-Agent': 'termux_repo-license-audit'})
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read(1024 * 1024 + 1)
            assert hashlib.sha256(data).hexdigest() == expected_hash, (identity, url)
            fetched[url] = data
        (target / 'UPSTREAM-LICENSE.txt').write_bytes(fetched[url])
        notices.append({'path': 'UPSTREAM-LICENSE.txt', 'source': url, 'sha256': expected_hash})
        record = {
            'package': identity, 'license': entries.get('license'),
            'copyright': entries.get('copyright'), 'nuget_sha512': sha512,
            'notices': notices,
        }
        if name == 'monomod.core':
            record['replacement'] = 'Assembly rebuilt from the pinned source with the application-local Bionic port; see changes/ and the package source licenses.'
        records.append(record)
    (out / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    collect(*map(Path, sys.argv[1:]))
