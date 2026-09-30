import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotbot.plugin import Plugin


class Install(Plugin):
    supports_dry_run = True

    _directive = "install"
    _operations = {"apply", "status", "upgrade"}
    _states = {
        "absent",
        "blocked",
        "current",
        "drifted",
        "unsupported",
        "update-available",
    }
    _mutation_success_states = {"current", "unsupported", "update-available"}

    def can_handle(self, directive: str) -> bool:
        return directive == self._directive

    def handle(self, directive: str, data: Any) -> bool:
        if directive != self._directive:
            raise ValueError("Install cannot handle directive {}".format(directive))
        configured_installers = self._configured_installers(data)
        if configured_installers is None:
            return False

        operation = os.environ.get("DOTBOT_INSTALL_OPERATION", "apply").strip().lower()
        if operation not in self._operations:
            self._log.error("Unsupported installer operation: {}".format(operation))
            return False

        host_family = self._host_family()
        prepared = self._prepare_installers(
            configured_installers,
            operation,
            host_family,
        )
        if prepared is None:
            return False

        if self._context.dry_run():
            for installer_argv, description, _ in prepared:
                self._log.action(
                    "Would run installer {} {}".format(description, installer_argv)
                )
            return True

        for installer_argv, description, command in prepared:
            self._log.action("{} {}".format(description, installer_argv))
            if not self._run_installer(command, str(installer_argv), operation):
                return False
        return True

    def _configured_installers(
        self, data: Any
    ) -> Optional[List[Tuple[List[str], str]]]:
        if not isinstance(data, list) or not data:
            self._log.error(
                "Install directives require a non-empty list of "
                "[installer command, description] entries"
            )
            return None

        configured_installers = []
        for index, value in enumerate(data, start=1):
            if not isinstance(value, list) or len(value) != 2:
                self._log.error(
                    "Install directive entry {} must contain "
                    "[installer command, description]".format(index)
                )
                return None
            command_value, description = value
            if isinstance(command_value, str):
                installer_argv = [command_value.strip()]
            elif isinstance(command_value, list):
                installer_argv = list(command_value)
            else:
                installer_argv = []
            if (
                not installer_argv
                or not all(isinstance(argument, str) for argument in installer_argv)
                or not installer_argv[0].strip()
            ):
                self._log.error(
                    "Install directive entry {} command must be an installer path "
                    "or a non-empty argument list beginning with one".format(index)
                )
                return None
            installer_argv[0] = installer_argv[0].strip()
            if not isinstance(description, str) or not description.strip():
                self._log.error(
                    "Install directive entry {} description must be a non-empty string".format(
                        index
                    )
                )
                return None
            configured_installers.append((installer_argv, description.strip()))
        return configured_installers

    def _prepare_installers(
        self,
        configured_installers: List[Tuple[List[str], str]],
        operation: str,
        host_family: str,
    ) -> Optional[List[Tuple[List[str], str, List[str]]]]:
        prepared = []
        valid = True
        for installer_argv, description in configured_installers:
            configured_path, installer_arguments = installer_argv[0], installer_argv[1:]
            resolved = self._resolve_installer(configured_path)
            if resolved is None:
                valid = False
                continue
            installer_path, affinity = resolved
            if affinity != "shared" and affinity != host_family:
                self._log.error(
                    "Installer {} targets {}, but Dotbot is running on {}".format(
                        configured_path, affinity, host_family
                    )
                )
                valid = False
                continue

            command = self._command(
                installer_path,
                installer_arguments,
                operation,
                host_family,
            )
            if command is None:
                valid = False
                continue
            prepared.append((installer_argv, description, command))
        return prepared if valid else None

    def _run_installer(
        self,
        command: List[str],
        installer_command: str,
        operation: str,
    ) -> bool:
        environment = self._environment()

        try:
            result = subprocess.run(
                command,
                cwd=self._context.base_directory(),
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError as error:
            self._log.error(
                "Unable to run installer {}: {}".format(installer_command, error)
            )
            return False

        output = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        state = output[0] if len(output) == 1 else None
        succeeded = result.returncode == 0 and state in self._states
        if succeeded and operation != "status":
            succeeded = state in self._mutation_success_states

        self._log_diagnostics(result.stderr, succeeded)
        if result.returncode != 0:
            self._log.error(
                "Installer {} exited with status {}".format(
                    installer_command, result.returncode
                )
            )
            return False
        if state not in self._states or len(output) != 1:
            self._log.error(
                "Installer {} must emit exactly one lifecycle state on stdout".format(
                    installer_command
                )
            )
            return False
        if not succeeded:
            self._log.error(
                "Installer {} did not converge: {}".format(installer_command, state)
            )
            return False

        self._log.info("{}: {}".format(installer_command, state))
        return True

    def _resolve_installer(self, configured_path: str) -> Optional[Tuple[Path, str]]:
        repo_root = Path(self._context.base_directory()).resolve()
        install_root = (repo_root / "install").resolve()
        configured = Path(configured_path)
        if configured.is_absolute() or configured.drive:
            self._log.error("Installer paths must be relative to the Dotbot repository")
            return None

        installer_path = (repo_root / configured).resolve()
        try:
            relative = installer_path.relative_to(install_root)
        except ValueError:
            self._log.error("Installer paths must remain within the repository install directory")
            return None

        if not installer_path.is_file():
            self._log.error("Installer does not exist or is not a file: {}".format(configured_path))
            return None
        if not relative.parts or relative.parts[0].lower() not in {"shared", "unix", "windows"}:
            self._log.error("Installers must live under install/shared, install/unix, or install/windows")
            return None

        affinity = relative.parts[0].lower()
        return installer_path, affinity

    def _command(
        self,
        installer_path: Path,
        installer_arguments: List[str],
        operation: str,
        host_family: str,
    ) -> Optional[List[str]]:
        suffix = installer_path.suffix.lower()
        if suffix == ".py":
            command = [sys.executable, str(installer_path)]
        elif host_family == "windows" and suffix == ".ps1":
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if powershell is None:
                self._log.error("PowerShell is required to run {}".format(installer_path.name))
                return None
            command = [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(installer_path),
            ]
        elif host_family == "unix" and os.access(str(installer_path), os.X_OK):
            command = [str(installer_path)]
        else:
            self._log.error(
                "Installer {} is not executable by the current platform host".format(installer_path.name)
            )
            return None

        command.extend(installer_arguments)
        command.append(operation)
        return command

    def _environment(self) -> Dict[str, str]:
        repo_root = Path(self._context.base_directory()).resolve()
        environment = os.environ.copy()
        environment.update(
            {
                "DOTBOT_INSTALL_REPO_ROOT": str(repo_root),
            }
        )
        environment.pop("DOTBOT_INSTALL_ONLINE", None)
        environment.pop("DOTBOT_INSTALL_OPERATION", None)
        return environment

    @staticmethod
    def _host_family() -> str:
        return "windows" if os.name == "nt" else "unix"

    def _log_diagnostics(self, diagnostics: str, succeeded: bool) -> None:
        for line in diagnostics.splitlines():
            line = line.strip()
            if not line:
                continue
            if succeeded:
                self._log.info(line)
            else:
                self._log.warning(line)
