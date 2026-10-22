# copyparty 1.20.26

Python HTTP file server with a web UI, resumable uploads and WebDAV.
Install after the [repository setup](../../README.md):

```sh
pacman -Syu termux_repo-aarch64/copyparty
mkdir -p "$HOME/shared-files"
copyparty -i 127.0.0.1 -p 3923 -v "$HOME/shared-files:/shared:rw"
```

Open `http://127.0.0.1:3923/shared/` on the device. The example grants read/write
access only to the selected directory and binds to loopback. Choose accounts,
volume permissions and the intended bind address before serving other devices.
No server is started during installation, and existing files are not changed.
Android storage access and background process restrictions still apply.

The core uses official Termux `python`. Jinja2 3.1.6 and MarkupSafe 3.0.3 are
mandatory template dependencies absent from the pinned official Termux recipe
tree; their checksum-pinned sources are installed privately under
`$PREFIX/lib/copyparty`, with MarkupSafe's pure Python fallback. Pacman owns
these files. There are no runtime pip hooks, global site-package writes, or
network downloads at startup.

Optional media tools are not mandatory dependencies. Reuse official `ffmpeg`
for media inspection/transcoding and `python-pillow` for image thumbnails when
needed. Official `libvips` alone does not include the optional Python `pyvips`
binding. SFTP/FTP/TFTP and optional Python integrations are not advertised as
enabled by this core package. Existing compatible system Python modules remain
available to the application.

[Upstream source](https://github.com/9001/copyparty/tree/v1.20.26) and
[Termux instructions](https://github.com/9001/copyparty/tree/v1.20.26#install-on-android).
The release source includes the web assets and their notices. Copyparty is MIT;
Jinja2/MarkupSafe are BSD-3-Clause, and included web assets/fonts have the
additional licenses recorded in `copyparty/res/COPYING.txt`. The package keeps
those notices and the complete upstream license texts under
`$PREFIX/share/doc/copyparty`. See `dependencies.json` for the private inputs.
TUR tree `129d9f5e06a37f19313833b640d7bf0f7eb781f5` had no copyparty recipe.

`python packages/copyparty/smoke-test.py` checks the HTML UI, uploads a generated
file over loopback, and verifies the downloaded bytes in a temporary directory.
The native Termux package still needs its build/runtime release gate; host
Python tests do not establish Android compatibility.
