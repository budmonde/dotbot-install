# dotbot-install

`dotbot-install` adds one lifecycle-aware installer directive to
[Dotbot](https://github.com/anishathalye/dotbot).
Dotbot continues to select and order installers; this plugin validates and invokes each selected script through a small protocol.

## Dotbot directive

Load `install.py` as a Dotbot plugin, then place one installer path in each directive:

```yaml
- install: install/unix/texlive
- install: install/shared/example.py
```

The value must be a relative path to one file below `install/unix/`, `install/windows/`, or `install/shared/` in the repository Dotbot is applying.
One directive invokes exactly one installer.

Platform affinity is structural.
`install/windows/` runs only from a Windows Dotbot process, while `install/unix/` runs only from Linux, macOS, or WSL.
A mismatch is a configuration failure and the script is not executed.
`install/shared/` is available on both host families.

## Installer protocol

The plugin calls the script with one of these argument forms:

```text
<installer> status
<installer> apply
<installer> upgrade [requested-version]
```

`apply` is the default.
Launchers select another operation through `DOTBOT_INSTALL_OPERATION` and may set `DOTBOT_INSTALL_VERSION` for `upgrade`.

The script must print exactly one of these states on standard output:

- `absent`
- `current`
- `drifted`
- `update-available`
- `blocked`
- `unsupported`

Diagnostics belong on standard error.
An installer failure uses a nonzero exit status.

`status` must be read-only.
`apply` must idempotently install an absent target or repair the locked target without advancing its version.
`upgrade` is the only operation that may advance a version, and a script must update lock data only after it has verified the installed result.

After `apply` or `upgrade`, `current`, `update-available`, and `unsupported` are successful outcomes.
`absent`, `drifted`, and `blocked` fail the Dotbot action because the requested mutation did not converge.
All six states are valid informational results during `status`.

The child process receives:

| Variable | Meaning |
| --- | --- |
| `DOTBOT_INSTALL_PROTOCOL_VERSION` | Protocol version, currently `1`. |
| `DOTBOT_INSTALL_OPERATION` | `status`, `apply`, or `upgrade`. |
| `DOTBOT_INSTALL_VERSION` | Requested upgrade version when one was supplied. |
| `DOTBOT_INSTALL_ID` | Installer path relative to the owning repository. |
| `DOTBOT_INSTALL_REPO_ROOT` | Canonical path to the owning repository. |
| `DOTBOT_INSTALL_STATE_DIR` | Stable per-installer state directory. |
| `DOTBOT_INSTALL_LOCK_FILE` | Conventional repository lock path, `install/installer.lock.yaml`. |
| `DOTBOT_INSTALL_ONLINE` | `1` unless the launcher explicitly disables online work. |

The plugin does not create state or lock files and does not implement package-manager or release backends.
Those remain owned by the repository's `install/` tree.

## Script hosts

Python installers run with the Python interpreter already running Dotbot.
On Windows, `.ps1` installers run with PowerShell 7 when available and Windows PowerShell otherwise.
On Unix-family hosts, other installer files must be executable and provide their own shebang.

Dotbot dry-run logs the installer that would run without starting the child process.
Paths are canonicalized before execution, and paths or symlinks that escape the owning repository's `install/` directory are rejected.

## Development

Install the test dependencies and run the suite:

```text
python -m pip install -e ".[test]"
python -m pytest
```
