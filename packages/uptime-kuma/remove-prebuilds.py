#!/usr/bin/env python3
"""Exclude foreign native payloads before building the one Android addon."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
removed = []
for path in root.rglob('*'):
    if not path.is_file() or path.is_symlink():
        continue
    with path.open('rb') as stream:
        magic = stream.read(4)
    if (path.suffix.lower() in ('.node', '.so', '.dll', '.exe', '.dylib', '.a')
            or magic in (b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe')
            or magic[:2] == b'MZ'):
        removed.append(str(path.relative_to(root)))
        path.unlink()
print('Excluded foreign native payloads:', ', '.join(removed))
