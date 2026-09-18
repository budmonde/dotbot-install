# dotbot-install

`dotbot-install` adds one lifecycle-aware installer directive and runner to [Dotbot](https://github.com/anishathalye/dotbot).
Dotbot continues to select and order installers.
The plugin validates and invokes each selected installer command through a small protocol.

## Dotbot directive

Load `install.py` as a Dotbot plugin,
then provide an ordered list of command-description pairs:

```yaml
- install:
    - [install/shared/example.py, Installing the shared example]
    - [[install/unix/example, configured-target, --version, "1.2.3"], Installing the Unix example]
```

An entry contains exactly:

```text
[installer-path, description]
[[installer-path, configured-argument, ...], description]
```

An installer-path string is shorthand for a one-item argument list.
Use a nested list when an installer needs configured arguments.
Each list item becomes exactly one process argument without shell parsing.
The first command item must resolve to a file below `install/unix/`,
`install/windows/`,
or `install/shared/` in the repository Dotbot is applying.
The description must be a non-empty string.
Installer-specific configuration belongs in the command,
including an optional `--version <desired-version>` argument when the installer supports exact versions.
The plugin treats configured arguments as opaque and never passes them through a shell.

The plugin includes the installer argument list in its output,
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
<installer> [configured-arguments...] status
<installer> [configured-arguments...] apply
<installer> [configured-arguments...] upgrade
```

`apply` is the default.
The runner selects upgrade mode through `--upgrade`.
The lifecycle operation is always the final argument appended by the plugin.

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
`upgrade` may advance an unpinned manager-controlled resource.
An exact version configured in the installer command remains authoritative for every operation.

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
| `DOTBOT_INSTALL_REPO_ROOT` | Canonical path to the owning repository. |
| `DOTBOT_INSTALL_ONLINE` | `1` unless the launcher disables online work. |

The plugin does not define installer identity,
state storage,
lock files,
package-manager behavior,
or release policy.
Those remain owned by the consuming repository and its installer commands.

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

## Agent skill

The repository publishes `skills/dotbot-install-authoring/` for agents that author or review consuming-repository installers.
The skill covers ownership decisions,
minimal lifecycle design,
interactive-process constraints,
destructive-operation boundaries,
and proportionate verification in addition to the wire protocol above.
