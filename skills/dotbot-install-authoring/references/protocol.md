# Dotbot install protocol

## Directive entry

The plugin accepts a nonempty ordered list of entries in either form:

```yaml
- install:
    - [install/shared/example.py, Installing the shared example]
    - [install/unix/example, Installing the Unix example, "1.2.3"]
```

The first item is a repository-relative installer path,
the second is the nonempty description logged before execution,
and the optional third item is a quoted exact version.
The plugin preflights the whole list and stops after the first execution failure.

Platform affinity follows the first path component:

- `install/shared/` runs on Windows and Unix-family hosts;
- `install/windows/` runs only on Windows;
- `install/unix/` runs on Linux,
  macOS,
  and WSL.

## Script interface

The plugin invokes one of these forms:

```text
<installer> status [desired-version]
<installer> apply [desired-version]
<installer> upgrade [desired-version]
```

The child receives:

| Variable | Meaning |
| --- | --- |
| `DOTBOT_INSTALL_PROTOCOL_VERSION` | Protocol version, currently `2`. |
| `DOTBOT_INSTALL_OPERATION` | `status`, `apply`, or `upgrade`. |
| `DOTBOT_INSTALL_DESIRED_VERSION` | Current entry's exact desired version, or unset. |
| `DOTBOT_INSTALL_ID` | Installer path relative to the consuming repository. |
| `DOTBOT_INSTALL_REPO_ROOT` | Canonical consuming-repository path. |
| `DOTBOT_INSTALL_STATE_DIR` | Stable per-repository, per-installer state directory. |
| `DOTBOT_INSTALL_LOCK_FILE` | Conventional consuming-repository integrity-lock path. |
| `DOTBOT_INSTALL_ONLINE` | `1` unless the launcher disables online work. |

The plugin does not create the state directory or lock file.
The consuming repository owns their use.

## Output and states

The installer emits exactly one state on stdout:

| State | Meaning |
| --- | --- |
| `absent` | The intended resource is missing. |
| `current` | Observed state satisfies recipe intent. |
| `drifted` | Owned state exists but is incomplete, unusable, or differs from recipe intent. |
| `update-available` | An acceptable unpinned owned state has a newer candidate. |
| `blocked` | A prerequisite or external condition prevents a reliable decision or action. |
| `unsupported` | Detected state is intentionally outside resource ownership and is acceptable to preserve. |

Diagnostics go to stderr.
Unexpected execution failures use a nonzero exit status.

All six states are informational during `status`.
After `apply` or `upgrade`,
`current`,
`update-available`,
and `unsupported` are successful outcomes.
`absent`,
`drifted`,
and `blocked` mean mutation did not converge.

## Operation policy

`status` is read-only.
Optional update discovery must respect `DOTBOT_INSTALL_ONLINE` and must not invalidate an otherwise acceptable installation when discovery alone fails.

For an unpinned resource:

- `apply` installs or repairs absent or drifted owned state without advancing an acceptable installed version;
- `upgrade` may request the newest acceptable manager or upstream candidate.

For an exact recipe version:

- the third entry item is the sole version-selection authority;
- `status` compares against that target;
- `apply` converges that target,
  including a supported owned downgrade;
- `upgrade` may converge the target but never move past it;
- a backend that cannot honor an exact target rejects it rather than silently ignoring it.

## Process boundary

The plugin invokes installers with null stdin and captures stdout and stderr until the child exits.
Only the recipe description is logged before execution.
The default protocol therefore supports unattended children,
not live prompts or device-code instructions.

Python resources use the interpreter already running Dotbot.
Windows PowerShell resources use PowerShell 7 when available and Windows PowerShell otherwise,
with `-NonInteractive`.
Unix resources other than Python must be executable and provide their own shebang.

Dotbot dry-run logs prepared resources without starting child processes.
The plugin rejects absolute paths,
missing files,
platform mismatches,
and resolved paths that escape the consuming repository's `install/` tree.

## Ownership boundary

The plugin supplies no package-manager,
release,
authentication,
or application backend.
It also does not define which external state a resource may replace.
Those policies belong to the consuming repository and its accepted resource contract.
