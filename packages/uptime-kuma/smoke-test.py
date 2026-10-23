#!/usr/bin/env python3
"""Run the local synthetic integration test with the installed Node runtime."""
import os
from pathlib import Path
import subprocess

root = os.environ.get('UPTIME_KUMA_TEST_ROOT', '/data/data/com.termux/files/usr/lib/uptime-kuma')
subprocess.run(['node', str(Path(__file__).with_name('smoke-test.cjs')), root], check=True, timeout=240)
