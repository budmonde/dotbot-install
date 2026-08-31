# dotbot-install

`dotbot-install` adds one lifecycle-aware installer directive and runner to [Dotbot](https://github.com/anishathalye/dotbot).
Dotbot continues to select and order installers.
The plugin validates and invokes each selected script through a small protocol.

## Dotbot directive

Load `install.py` as a Dotbot plugin,
then provide an ordered list of path-description pairs with optional exact versions:

```yaml
- install:
    - [install/shared/example.py, Installing the shared example]
    - [install/unix/example, Installing the Unix example, "1.2.3"]
```

An entry contains exactly:

```text
[installer-path, description]
[installer-path, description, "desired-version"]
```

The path must resolve to a file below `install/unix/`,
`install/windows/`,
or `install/shared/` in the repository Dotbot is applying.
The description must be a non-empty string.
The optional desired version must be a non-empty string and should always be quoted in YAML.

The plugin includes the installer path in its output,
preflights every entry before execution,
runs entries in declaration order,
and stops after the first execution failure.

Platform affinity is structural.
`install/windows/` runs only from a Windows Dotbot process.
`install/unix/` runs only from Linux,
macOS,
or WSL.
`install/shared/` is available on both host families.

## Installer protocol

The plugin calls the script through one of these forms:

```text
<installer> status [desired-version]
<installer> apply [desired-version]
<installer> upgrade [desired-version]
```

`apply` is the default.
The runner selects upgrade mode through `--upgrade`.
The optional version belongs to the current directive entry and is passed for every operation.

The script prints exactly one lifecycle state to standard output:

- `absent`
- `current`
- `drifted`
- `update-available`
- `blocked`
- `unsupported`

Diagnostics belong on standard error.
An unexpected installer failure uses a nonzero exit status.

`status` must be read-only.
`apply` must idempotently converge recipe intent without upgrading an existing unpinned resource.
`upgrade` may advance an unpinned manager-controlled resource,
but an exact recipe version remains authoritative.

After `apply` or `upgrade`,
`current`,
`update-available`,
and `unsupported` are successful outcomes.
`absent`,
`drifted`,
and `blocked` fail because the requested mutation did not converge.
All six states are informational during `status`.

The child process receives:

| Variable | Meaning |
| --- | --- |
| `DOTBOT_INSTALL_PROTOCOL_VERSION` | Protocol version, currently `2`. |
| `DOTBOT_INSTALL_OPERATION` | `status`, `apply`, or `upgrade`. |
| `DOTBOT_INSTALL_DESIRED_VERSION` | The current entry's exact desired version, or unset. |
| `DOTBOT_INSTALL_ID` | Installer path relative to the owning repository. |
| `DOTBOT_INSTALL_REPO_ROOT` | Canonical path to the owning repository. |
| `DOTBOT_INSTALL_STATE_DIR` | Stable per-installer state directory. |
| `DOTBOT_INSTALL_LOCK_FILE` | Conventional repository integrity-lock path. |
| `DOTBOT_INSTALL_ONLINE` | `1` unless the launcher disables online work. |

The plugin does not create state or lock files and does not implement package-manager or release backends.
Those remain owned by the consuming repository.

## Lifecycle runner

Dotbot parses its CLI before loading plugins,
so plugins cannot register `--upgrade` directly.
`runner.py` partially parses lifecycle flags,
sets `DOTBOT_INSTALL_OPERATION`,
and invokes unmodified Dotbot with every remaining argument unchanged.

```text
dotbot-install-runner path/to/dotbot --only install --dry-run --upgrade
```

Argument abbreviation is disabled.
Unknown options,
`--help`,
and `--version` remain Dotbot arguments.
An optional `--` bridge is accepted but not required.

Consumers may import `run_dotbot` when a repository-specific launcher must assemble Dotbot configuration arguments first.

## Script hosts

Python installers run with the Python interpreter already running Dotbot.
On Windows,
`.ps1` installers run with PowerShell 7 when available and Windows PowerShell otherwise.
On Unix-family hosts,
other installer files must be executable and provide their own shebang.

Dotbot dry-run logs every installer that would run without starting a child process.
Paths are canonicalized before execution.
Paths or symlinks that escape the owning repository's `install/` directory are rejected.

## Development

Install the test dependencies and run the suite:

```text
python -m pip install -e ".[test]"
python -m pytest
```
