# Dotbot install protocol

## Directive entry

The plugin accepts a nonempty ordered list of command-description entries:

```yaml
- install:
    - [install/shared/example.py, Installing the shared example]
    - [[install/unix/example, configured-target, --version, "1.2.3"], Installing the Unix example]
```

The first item is a repository-relative installer path or argument list, and the second is the nonempty description logged before execution.
An installer-path string is shorthand for a one-item argument list.
Use a nested list when an installer needs configured arguments.
Each list item becomes exactly one process argument without shell parsing.
Installer-specific configuration belongs in the command, including an optional `--version <desired-version>` argument when the installer supports exact versions.
The plugin preflights the whole list and stops after the first execution failure.

Platform affinity follows the first command item's path component:

- `install/shared/` runs on Windows and Unix-family hosts;
- `install/windows/` runs only on Windows;
- `install/unix/` runs on Linux, macOS, and WSL.

## Script interface

The plugin invokes one of these forms:

```text
<installer> [configured-arguments...] status
<installer> [configured-arguments...] apply
<installer> [configured-arguments...] upgrade
```

The child receives:

| Variable | Meaning |
| --- | --- |
| `DOTBOT_INSTALL_REPO_ROOT` | Canonical consuming-repository path. |

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
After `apply` or `upgrade`, `current`, `update-available`, and `unsupported` are successful outcomes.
`absent`, `drifted`, and `blocked` mean mutation did not converge.

## Operation policy

`status` is read-only.
`status` uses locally available state and must not make network requests to discover updates.

For an unpinned resource:

- `apply` installs or repairs absent or drifted owned state without advancing an acceptable installed version;
- `upgrade` may request the newest acceptable manager or upstream candidate.

For an exact recipe version:

- the installer command's version argument is the sole version-selection authority;
- `status` compares against that target;
- `apply` converges that target, including a supported owned downgrade;
- `upgrade` may converge the target but never move past it;
- a backend that cannot honor an exact target rejects it rather than silently ignoring it.

## Process boundary

The plugin invokes installers with null stdin and captures stdout and stderr until the child exits.
The recipe description and configured installer argument list are logged before execution.
Installer commands must not contain secrets.
The default protocol therefore supports unattended children, not live prompts or device-code instructions.

Python resources use the interpreter already running Dotbot.
Windows PowerShell resources use PowerShell 7 when available and Windows PowerShell otherwise, with `-NonInteractive`.
Unix resources other than Python must be executable and provide their own shebang.

Dotbot dry-run logs prepared resources without starting child processes.
The plugin rejects absolute paths, missing files, platform mismatches, and resolved paths that escape the consuming repository's `install/` tree.

## Ownership boundary

The plugin supplies no package-manager, release, authentication, application backend, installer identity, state directory, or lock-file convention.
It also does not define which external state a resource may replace.
Those policies belong to the consuming repository and its accepted resource contract.
