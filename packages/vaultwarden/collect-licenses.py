#!/usr/bin/env python3
"""Preserve dependency license/notice files and a manifest for the actual build.

Input is cargo metadata or the JSON stream from go list -deps. Missing crate
notices are read from the exact Git revision recorded in the crate archive.
No downloaded code is executed. Cargo metadata includes build dependencies.
"""
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import hashlib
import tomllib
import urllib.request
import urllib.error

# These exact published revisions declare MIT OR Apache-2.0 but contain no
# license/notice file, including in their complete upstream Git tree. Exercise
# the declared Apache-2.0 option, retaining the authors and original declaration.
# This is not a purported upstream notice or an inferred license grant.
DECLARED_APACHE_ONLY = {
    ('pear', '0.2.9'): 'f803fa9daf1a022f1a216a16da2a0778474ecd43',
    ('pear_codegen', '0.2.9'): 'f803fa9daf1a022f1a216a16da2a0778474ecd43',
    ('stable-pattern', '0.1.0'): '92d65ff4ac1d3acb0b7c7bc3fa33e056cbab9607',
}
APACHE_TEXT_HASH = 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30'

kind, source, destination = sys.argv[1:]
out = Path(destination)
out.mkdir(parents=True, exist_ok=True)
raw = Path(source).read_text()
modules = {}
source_urls = {}
if kind == 'cargo':
    for package in json.loads(raw)['packages']:
        if package['source'] is not None:
            modules[package['id']] = (package['name'] + '-' + package['version'], Path(package['manifest_path']).parent, package.get('license'), package.get('license_file'))
            source_urls[package['id']] = (f"https://crates.io/api/v1/crates/{package['name']}/{package['version']}/download"
                if package['source'].startswith('registry+') else package['source'])
elif kind == 'go':
    decoder = json.JSONDecoder()
    while raw.strip():
        value, offset = decoder.raw_decode(raw.lstrip())
        raw = raw.lstrip()[offset:]
        module = value.get('Module', {})
        if module and not module.get('Main'):
            module = module.get('Replace') or module
            identity = module['Path'] + '@' + module.get('Version', 'local')
            modules[identity] = (identity, Path(module['Dir']), None, None)
else:
    raise SystemExit('expected cargo or go')

manifest = []
for identity, (label, directory, license_id, license_file) in sorted(modules.items()):
    safe = re.sub(r'[^a-zA-Z0-9._@+-]', '_', label)
    copied = []
    candidates = set()
    for path in directory.rglob('*'):
        if path.is_file() and (re.match(r'^(licen[cs]e|copying|copyright|notice|authors)([._-]|$)', path.name, re.I) or 'licenses' in [p.lower() for p in path.relative_to(directory).parts[:-1]]):
            candidates.add(path)
    if license_file:
        candidates.add(directory / license_file)
    for path in sorted(candidates):
        relative = path.relative_to(directory)
        target = out / safe / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        copied.append(str(relative).replace('\\', '/'))
    fetched = []
    if not copied and kind == 'cargo':
        vcs = directory / '.cargo_vcs_info.json'
        package = tomllib.loads((directory / 'Cargo.toml').read_text())['package']
        # Some crates identify their repository only by a GitHub homepage, or
        # point at a workspace subdirectory. The archive's Git SHA still pins
        # the source; never use the homepage's moving branch name.
        repository = ''
        for field in ('repository', 'homepage'):
            match = re.match(r'^https://github.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/|$)', package.get(field, ''))
            if match:
                repository = 'https://github.com/' + match[1] + '/' + match[2].removesuffix('.git')
                break
        vcs_info = json.loads(vcs.read_text()) if vcs.is_file() else {}
        commit = vcs_info.get('git', {}).get('sha1', '')
        # These 2018 import-library archives predate cargo_vcs_info.json.
        # Every shipped source/build/library byte (1390 and 1419 files) and
        # Cargo.toml.orig was compared with this upstream publication commit.
        if not commit and package['name'] in ('winapi-i686-pc-windows-gnu', 'winapi-x86_64-pc-windows-gnu') and package['version'] == '0.4.0':
            assert package['license'] == 'MIT/Apache-2.0'
            commit = '9497609ef44cc9bcd16cd2411c0ee6ccaf5483aa'
            vcs_info['path_in_vcs'] = 'i686' if 'i686' in package['name'] else 'x86_64'
        # This optional WASM dependency omits repository metadata. Its sibling
        # sqlite-wasm-rs archive identifies the repository at the same Git SHA.
        if package['name'] == 'rsqlite-vfs' and package['version'] == '0.1.1' and commit == '1bb309784f25c401ddf95131dcde4c4cdad7aee7':
            repository = 'https://github.com/Spxg/sqlite-wasm-rs'
        declared_apache = DECLARED_APACHE_ONLY.get((package['name'], package['version'])) == commit
        if declared_apache:
            assert package['license'] == 'MIT OR Apache-2.0'
            content = (Path(__file__).parent / 'license-texts/Apache-2.0.txt').read_bytes()
            assert hashlib.sha256(content).hexdigest() == APACHE_TEXT_HASH
            target = out / safe
            target.mkdir(parents=True, exist_ok=True)
            (target / 'Apache-2.0.txt').write_bytes(content)
            shutil.copyfile(directory / 'Cargo.toml', target / 'UPSTREAM-Cargo.toml')
            shutil.copyfile(vcs, target / 'UPSTREAM-cargo_vcs_info.json')
            (target / 'LICENSE-SELECTION.txt').write_text(
                'The upstream manifest declares MIT OR Apache-2.0. This distribution selects Apache-2.0.\n'
                'No LICENSE/NOTICE file is present in this exact crate or its upstream Git tree.\n'
                'Apache-2.0.txt is the standard license text, not an upstream notice.\n'
                'License text: https://www.apache.org/licenses/LICENSE-2.0.txt\n'
                'Authors (as declared upstream): ' + ', '.join(package.get('authors', [])) + '\n'
                'Source: ' + repository + '/tree/' + commit + '\n')
            copied.extend(['Apache-2.0.txt', 'UPSTREAM-Cargo.toml', 'UPSTREAM-cargo_vcs_info.json', 'LICENSE-SELECTION.txt'])
        if re.fullmatch(r'https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) and re.fullmatch(r'[0-9a-f]{40}', commit):
            subdir = PurePosixPath(vcs_info.get('path_in_vcs', ''))
            assert not subdir.is_absolute() and '..' not in subdir.parts
            locations = [PurePosixPath('.')]
            if subdir != PurePosixPath('.'):
                locations.extend([subdir, *[p for p in subdir.parents if p != PurePosixPath('.')]])
            for location in ([] if declared_apache else locations):
                for filename in ('LICENSE', 'LICENSE.txt', 'LICENSE.md', 'LICENSE-MIT', 'LICENSE-APACHE', 'LICENSE-ZLIB', 'COPYING',
                                 'LICENSE-MIT.txt', 'LICENSE-APACHE.txt', 'LICENSE.MIT', 'LICENSE.APACHE', 'LICENSE.BSD', 'LICENSE-2.0',
                                 'LICENSE-MIT.md', 'LICENSE-APACHE.md', 'COPYING.txt', 'NOTICE'):
                    relative = location / filename
                    url = repository.replace('https://github.com/', 'https://raw.githubusercontent.com/') + '/' + commit + '/' + str(relative)
                    try:
                        with urllib.request.urlopen(url, timeout=30) as response: content = response.read(262145)
                    except urllib.error.HTTPError as error:
                        if error.code == 404: continue
                        raise
                    if len(content) > 262144: raise SystemExit('Oversize license: ' + url)
                    target = out / safe / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content); copied.append(str(relative))
                    fetched.append({'url': url, 'sha256': hashlib.sha256(content).hexdigest()})
                if copied:
                    break
    if not copied:
        raise SystemExit('No license/notice found for ' + identity)
    # Include exact Cargo-verified source for MPL-only dependencies, alongside
    # their license, so recipients can obtain it directly with the executable.
    bundled_source = None
    if kind == 'cargo' and license_id and 'MPL-2.0' in license_id and ' OR ' not in license_id:
        shutil.copytree(directory, out / safe / 'source', ignore=shutil.ignore_patterns('.cargo-ok'))
        bundled_source = 'source'
    manifest.append({'dependency': identity, 'license': license_id, 'directory': safe, 'files': copied,
                     'source_url': source_urls.get(identity), 'bundled_source': bundled_source,
                     'upstream_notices': fetched})
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Preserved notices for', len(manifest), 'dependencies')
