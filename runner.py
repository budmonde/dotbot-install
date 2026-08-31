import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


OPERATIONS = {"apply", "status", "upgrade"}


class LifecycleArgumentError(ValueError):
    pass


class _LifecycleArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise LifecycleArgumentError(message)


def parse_lifecycle_arguments(
    arguments: Sequence[str], environment: Optional[Mapping[str, str]] = None
) -> Tuple[str, List[str]]:
    values = [value for value in arguments if value != "--"]
    parser = _LifecycleArgumentParser(add_help=False, allow_abbrev=False)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--upgrade", action="store_true")
    options, remaining = parser.parse_known_args(values)

    inherited = os.environ if environment is None else environment
    operation = "upgrade" if options.upgrade else inherited.get(
        "DOTBOT_INSTALL_OPERATION", "apply"
    ).strip().lower()
    if operation not in OPERATIONS:
        raise LifecycleArgumentError(
            "Unsupported installer operation: {}".format(operation)
        )
    return operation, remaining


def dotbot_environment(
    operation: str, environment: Optional[Mapping[str, str]] = None
) -> Dict[str, str]:
    result = dict(os.environ if environment is None else environment)
    result["DOTBOT_INSTALL_OPERATION"] = operation
    result.pop("DOTBOT_INSTALL_VERSION", None)
    result.pop("DOTBOT_INSTALL_DESIRED_VERSION", None)
    return result


def run_dotbot(
    dotbot: Path,
    arguments: Sequence[str],
    cwd: Optional[Path] = None,
    environment: Optional[Mapping[str, str]] = None,
    python: Optional[str] = None,
) -> int:
    operation, remaining = parse_lifecycle_arguments(arguments, environment)
    command = [python or sys.executable, str(dotbot), *remaining]
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=dotbot_environment(operation, environment),
        check=False,
    ).returncode


def propagate_returncode(returncode: int) -> int:
    if returncode < 0 and os.name != "nt":
        signum = -returncode
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
    return returncode


def main(arguments: Optional[Sequence[str]] = None) -> int:
    values = list(sys.argv[1:] if arguments is None else arguments)
    if not values:
        print("Expected: <dotbot path> [dotbot arguments]", file=sys.stderr)
        return 2
    dotbot = Path(values[0])
    try:
        return propagate_returncode(run_dotbot(dotbot, values[1:]))
    except (LifecycleArgumentError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
