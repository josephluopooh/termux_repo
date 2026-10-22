#!/usr/bin/env python3
"""Exercise the native CLI/server, a live subscription, and persistent SQLite."""
import tempfile
from smoke_support import *

with tempfile.TemporaryDirectory(prefix='ntfy-smoke-') as directory:
    work = Path(directory)
    env = environment(work)
    env = {k: v for k, v in env.items() if not k.startswith('NTFY_')}
    binary = os.environ.get('NTFY_BIN', 'ntfy')
    assert '2.32.0' in run([binary, '--version'], work, env)
    number = port()
    base = f'http://127.0.0.1:{number}'
    config = work / 'server.yml'
    config.write_text('listen-http: "127.0.0.1:' + str(number) + '"\nbase-url: "' + base + '"\nweb-root: "disable"\ncache-file: ' + json.dumps(str(work / 'cache.db')) + '\n')
    client = work / 'client.yml'
    client.write_text('{}\n')
    args = [binary, 'serve', '--config', str(config)]
    with daemon(args, work, env, 'server') as process:
        ready(number, process)
        # Open a streaming subscriber before publishing: the first event is "open".
        with HTTP.open(base + '/smoke/json', timeout=15) as response:
            assert json.loads(response.readline())['event'] == 'open'
            run([binary, 'publish', '--config', str(client), base + '/smoke', 'native-publish-roundtrip'], work, env)
            event = json.loads(response.readline())
            assert event['event'] == 'message' and event['message'] == 'native-publish-roundtrip', event
        events = run([binary, 'subscribe', '--config', str(client), '--poll', '--since', 'all', base + '/smoke'], work, env)
        assert 'native-publish-roundtrip' in events, events
    assert (work / 'cache.db').is_file()
    with daemon(args, work, env, 'restart') as process:
        ready(number, process)
        events = run([binary, 'subscribe', '--config', str(client), '--poll', '--since', 'all', base + '/smoke'], work, env)
        assert 'native-publish-roundtrip' in events, events
print('PASS ntfy: CLI publish/poll, live HTTP subscriber, SQLite cache survives restart')
