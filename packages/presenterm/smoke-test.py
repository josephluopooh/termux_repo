#!/usr/bin/env python3
"""Render generated content through a PTY in native Termux; no real user data."""
import fcntl
import os
from pathlib import Path
import pty
import re
import select
import sqlite3
import struct
import subprocess
import tempfile
import termios
import time

with tempfile.TemporaryDirectory(prefix='presenterm-smoke-') as directory:
    work = Path(directory)
    env = dict(os.environ, TERM='xterm-256color', COLORTERM='truecolor')
    for variable, name in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache')]:
        path = work / name
        path.mkdir()
        env[variable] = str(path)
    slides = work / 'slides.md'
    slides.write_text('# Native slide\n\nHello Termux\n')
    args = [os.environ.get('PRESENTERM_BIN', 'presenterm'), '--image-protocol', 'ascii-blocks', str(slides)]
    expected, quit_keys = 'Hello Termux', b'q'
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 36, 140, 1120, 576))
    process = subprocess.Popen(args, cwd=work, env=env, stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
    os.close(slave)
    output = b''
    found = False
    try:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if select.select([master], [], [], .2)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
                # Answer the terminal cursor query used by crossterm.
                if b'\x1b[6n' in chunk:
                    os.write(master, b'\x1b[1;1R')
                clean = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output)
                if expected.encode() in clean:
                    found = True
                    os.write(master, quit_keys)
                    break
            if process.poll() is not None:
                break
        assert found, output[-8000:]
        assert b'panicked at' not in output, output[-8000:]
        # Render success must also exit through the application's quit binding.
        # Drain the PTY while it exits so final terminal writes cannot block.
        deadline = time.monotonic() + 8
        while process.poll() is None and time.monotonic() < deadline:
            if select.select([master], [], [], .1)[0]:
                try:
                    output += os.read(master, 65536)
                except OSError:
                    break
        assert process.wait(timeout=2) == 0, output[-8000:]
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(5)
        os.close(master)
print('PASS presenterm: generated text rendered in PTY and clean quit')
