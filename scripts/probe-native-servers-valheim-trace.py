"""Print bounded diagnostic metadata; preserve the monitor's result in the shell."""
from pathlib import Path
import re
import sys

trace = Path(sys.argv[1])
lines = trace.read_text(errors='replace').splitlines() if trace.exists() else []
classes = {
    'certificate file accesses (successes and failures)': re.compile(
        r'/etc/(?:ssl|pki|tls)|ca-certificates|ca-bundle|cacert|cert\.pem|SSL_CERT', re.I),
    'kernel robust-list calls': re.compile(r'(?:get|set)_robust_list'),
    'failed shared-library file accesses': re.compile(r'\.so(?:[.\"/ ])[^\n]*= -1 (?:ENOENT|EACCES)'),
}
for title, pattern in classes.items():
    selected = [line for line in lines if pattern.search(line)]
    print('VALHEIM_TRACE', title, 'count=', len(selected), flush=True)
    print('\n'.join(selected[-200:]), flush=True)
print('No kernel robust-list entry does not imply no guest call: Termux glibc can return ENOSYS in userspace.', flush=True)

# Steam may direct its fatal diagnostic to a private log rather than stdout.
# This runs only inside the disposable probe container and prints selected lines.
pattern = re.compile(r'futex robust_list|Fatal error:|trusted SSL root|opensslconnection', re.I)
for folder in (Path.home()/'.steam/logs', Path.home()/'Steam/logs',
               Path.home()/'.local/share/Steam/logs'):
    if not folder.is_dir():
        continue
    for path in sorted(folder.glob('*')):
        if not path.is_file() or path.suffix not in ('.log', '.txt'):
            continue
        with path.open('rb') as stream:
            stream.seek(max(0, path.stat().st_size - 1048576))
            selected = [line for line in stream.read().decode('utf-8', 'replace').splitlines()
                        if pattern.search(line)]
        if selected:
            print('VALHEIM_STEAM_LOG', path, flush=True)
            print('\n'.join(selected[-80:]), flush=True)
