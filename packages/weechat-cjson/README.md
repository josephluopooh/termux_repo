# weechat-cjson

This WeeChat build enables cJSON, API relay, `/remote`, TLS, and the headless
binary while preserving the upstream Termux Android patches. The command is
still `weechat`; `weechat-headless` is also included. cJSON is built and published
alongside it.

Check [compatibility](../../README.md#compatibility) and complete the
[repository setup](../../README.md#repository-setup) before installing. The [recipe](build.sh) and
[releases](https://github.com/josephluopooh/termux_repo/releases) define the
source and published versions. For general use, see the
[upstream WeeChat documentation](https://weechat.org/doc/).

## Package variants and conflicts

`weechat-cjson` provides the versioned `weechat` capability and conflicts with
`weechat` and `weechat-dev`. The official and custom builds install the same
command and plugin paths, so they are **alternatives, not coinstallable packages**.
The distinct name keeps an ordinary official WeeChat update from replacing this
build; there is no broad `replaces` declaration.

Language plugins are separate packages:

| Custom package | Conflicting official plugin |
| --- | --- |
| `weechat-cjson-lua-plugin` | `weechat-lua-plugin` |
| `weechat-cjson-perl-plugin` | `weechat-perl-plugin` |
| `weechat-cjson-python-plugin` | `weechat-python-plugin` |
| `weechat-cjson-ruby-plugin` | `weechat-ruby-plugin` |

Each custom plugin depends on the **exact custom core version**. Keep the core
and its plugins together when switching packages.

## Install or switch from official WeeChat

1. Close WeeChat and back up `~/.config/weechat` and, if used, the legacy
   `~/.weechat` directory. Switching packages does not remove these directories,
   but upstream versions may migrate configuration formats.
2. Complete the [signed repository setup](../../README.md#repository-setup).
   Inspect any installed variants:

   ```sh
   pacman -Q | grep '^weechat'
   ```

3. Choose one full-upgrade transaction. If no language plugins are installed,
   install the custom core:

   ```sh
   pacman -Syu termux_repo-aarch64/weechat-cjson
   ```

   If language plugins are installed, use a combined command instead to switch
   them in the **same transaction** as the core. For example, for Python and Lua:

   ```sh
   pacman -Syu termux_repo-aarch64/weechat-cjson \
     termux_repo-aarch64/weechat-cjson-python-plugin \
     termux_repo-aarch64/weechat-cjson-lua-plugin
   ```

   Adjust the plugin list to match your installation and review Pacman's
   conflict/removal prompts before proceeding.

Update normally with `pacman -Syu`; partial upgrades are unsafe.

## Switch back to official WeeChat

Close WeeChat and keep configuration backups. Explicitly install `main/weechat`
and the corresponding official plugins in one transaction, reviewing conflict
prompts. For the Python and Lua example above:

```sh
pacman -Syu main/weechat main/weechat-python-plugin main/weechat-lua-plugin
```

Adjust the plugin list as needed. Keep the backups until you have checked the
configuration with the target version; switching packages does not undo upstream
configuration migrations.

## Verify the API

Inside WeeChat, use a new strong password and bind to localhost first:

```text
/set relay.network.bind_address 127.0.0.1
/set relay.network.password YOUR_OWN_STRONG_PASSWORD
/relay add ipv4.api 9000
```

Then, in another local terminal, run this command; curl prompts for the password:

```sh
curl --fail --user plain http://127.0.0.1:9000/api/version
```

A JSON response includes `weechat_version` and `relay_api_version`. Another
WeeChat instance can use `/remote add NAME URL -password=PASSWORD` followed by
`/remote connect NAME`. For access across a network, use a properly configured
`tls.api` relay or a secure tunnel; localhost HTTP is only the local smoke test.
See the [relay/API guide](https://weechat.org/files/doc/stable/weechat_user.en.html#relay_plugin)
and [API authentication](https://weechat.org/files/doc/weechat/stable/weechat_relay_api.en.html#authentication).

For automated package checks and their limits, see the
[build and test guide](../../docs/building.md#validation).

## Attribution and licensing

The recipe, patches, and plugin split originate from
[Termux-Pacman's pinned WeeChat source](https://github.com/termux-pacman/termux-packages/tree/7aae0e26de979162d09de28b05aaf3dd78592314/packages/weechat)
and are covered by WeeChat's GPL-3.0 license. The upstream checkout used for builds
is pinned in [sources.json](../../sources.json). cJSON retains its MIT license.
