import json
from argparse import Namespace
from pathlib import Path
from typing import List, Optional, Union
from unittest.mock import Mock

import pytest
from dotbot.context import Context

from install import Install


def make_plugin(repo: Path, dry_run: bool = False) -> Install:
    context = Context(str(repo), Namespace(dry_run=dry_run))
    return Install(context)


def installer(
    command: Union[str, List[str]], description: str = "Installing tool"
) -> list:
    return [command, description]


def write_python_installer(repo: Path, path: str, body: str) -> Path:
    installer = repo / path
    installer.parent.mkdir(parents=True, exist_ok=True)
    installer.write_text(body, encoding="utf-8")
    return installer


def python_installer(state: str, exit_code: int = 0, marker: Optional[Path] = None) -> str:
    lines = ["import sys"]
    if marker is not None:
        lines.extend(
            [
                "from pathlib import Path",
                "Path({!r}).write_text('ran', encoding='utf-8')".format(str(marker)),
            ]
        )
    lines.extend(["print({!r})".format(state), "raise SystemExit({})".format(exit_code)])
    return "\n".join(lines)


def recording_installer(marker: Path, name: str, state: str = "current") -> str:
    return "\n".join(
        [
            "from pathlib import Path",
            "with Path({!r}).open('a', encoding='utf-8') as stream:".format(str(marker)),
            "    stream.write({!r} + '\\n')".format(name),
            "print({!r})".format(state),
        ]
    )


def test_apply_runs_one_installer_and_accepts_current(tmp_path: Path) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current"),
    )

    assert make_plugin(tmp_path).handle(
        "install", [installer("install/shared/tool.py")]
    )


def test_description_is_logged_with_installer_path(tmp_path: Path) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current"),
    )
    plugin = make_plugin(tmp_path)
    action = Mock()
    plugin._log.action = action

    assert plugin.handle(
        "install", [installer("install/shared/tool.py", "Installing example tool")]
    )
    action.assert_called_once_with("Installing example tool ['install/shared/tool.py']")


def test_command_prefix_arguments_precede_operation(tmp_path: Path) -> None:
    result_file = tmp_path / "result.json"
    body = "\n".join(
        [
            "import json",
            "import sys",
            "from pathlib import Path",
            "Path({!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')".format(
                str(result_file)
            ),
            "print('current')",
        ]
    )
    write_python_installer(tmp_path, "install/shared/tool.py", body)

    assert make_plugin(tmp_path).handle(
        "install",
        [
            installer(
                [
                    "install/shared/tool.py",
                    "package-label",
                    "--version",
                    "2.0.0",
                    "SDK_HOME=Machine:Path:C:\\Program Files\\SDK",
                ]
            )
        ],
    )
    assert json.loads(result_file.read_text(encoding="utf-8")) == [
        "package-label",
        "--version",
        "2.0.0",
        "SDK_HOME=Machine:Path:C:\\Program Files\\SDK",
        "apply",
    ]


def test_command_prefix_is_logged(tmp_path: Path) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current"),
    )
    plugin = make_plugin(tmp_path)
    action = Mock()
    plugin._log.action = action

    assert plugin.handle(
        "install",
        [installer(["install/shared/tool.py", "package-label"], "Installing package")],
    )
    action.assert_called_once_with(
        "Installing package ['install/shared/tool.py', 'package-label']"
    )


def test_scalar_command_is_one_literal_installer_path(tmp_path: Path) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool with spaces.py",
        python_installer("current"),
    )

    assert make_plugin(tmp_path).handle(
        "install", [installer("install/shared/tool with spaces.py")]
    )


def test_list_runs_installers_in_order(tmp_path: Path) -> None:
    marker = tmp_path / "order"
    write_python_installer(
        tmp_path,
        "install/shared/first.py",
        recording_installer(marker, "first"),
    )
    write_python_installer(
        tmp_path,
        "install/shared/second.py",
        recording_installer(marker, "second"),
    )

    assert make_plugin(tmp_path).handle(
        "install",
        [
            installer("install/shared/first.py", "Installing first"),
            installer("install/shared/second.py", "Installing second"),
        ],
    )
    assert marker.read_text(encoding="utf-8").splitlines() == ["first", "second"]


@pytest.mark.parametrize(
    "data",
    [
        "install/shared/tool.py",
        [],
        {},
        ["install/shared/tool.py", "Installing tool"],
        [["install/shared/tool.py"]],
        [["install/shared/tool.py", "Installing tool", "1.2.3", "extra"]],
        [[7, "Installing tool"]],
        [[" ", "Installing tool"]],
        [["install/shared/tool.py", 7]],
        [["install/shared/tool.py", " "]],
        [["install/shared/tool.py", "Installing tool", 7]],
        [["install/shared/tool.py", "Installing tool", " "]],
        [[[], "Installing tool"]],
        [[[" ", "argument"], "Installing tool"]],
        [[["install/shared/tool.py", 7], "Installing tool"]],
    ],
)
def test_directive_rejects_invalid_payloads(tmp_path: Path, data: object) -> None:
    assert not make_plugin(tmp_path).handle("install", data)


def test_list_preflights_every_path_before_execution(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    write_python_installer(
        tmp_path,
        "install/shared/first.py",
        python_installer("current", marker=marker),
    )

    assert not make_plugin(tmp_path).handle(
        "install",
        [
            installer("install/shared/first.py", "Installing first"),
            installer("install/shared/missing.py", "Installing missing"),
        ],
    )
    assert not marker.exists()


def test_list_stops_after_first_execution_failure(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    write_python_installer(
        tmp_path,
        "install/shared/first.py",
        python_installer("blocked"),
    )
    write_python_installer(
        tmp_path,
        "install/shared/second.py",
        python_installer("current", marker=marker),
    )

    assert not make_plugin(tmp_path).handle(
        "install",
        [
            installer("install/shared/first.py", "Installing first"),
            installer("install/shared/second.py", "Installing second"),
        ],
    )
    assert not marker.exists()


def test_path_must_remain_under_install(tmp_path: Path) -> None:
    write_python_installer(tmp_path, "outside.py", python_installer("current"))

    assert not make_plugin(tmp_path).handle(
        "install", [installer("install/shared/../../outside.py")]
    )


def test_platform_mismatch_fails_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "marker"
    write_python_installer(
        tmp_path,
        "install/unix/tool.py",
        python_installer("current", marker=marker),
    )
    monkeypatch.setattr(Install, "_host_family", staticmethod(lambda: "windows"))

    assert not make_plugin(tmp_path).handle(
        "install", [installer("install/unix/tool.py")]
    )
    assert not marker.exists()


def test_dry_run_does_not_execute_installer(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current", marker=marker),
    )

    assert make_plugin(tmp_path, dry_run=True).handle(
        "install", [installer("install/shared/tool.py")]
    )
    assert not marker.exists()


@pytest.mark.parametrize("state", ["absent", "blocked", "drifted"])
def test_apply_requires_a_converged_state(tmp_path: Path, state: str) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer(state),
    )

    assert not make_plugin(tmp_path).handle(
        "install", [installer("install/shared/tool.py")]
    )


@pytest.mark.parametrize(
    "state",
    ["absent", "blocked", "current", "drifted", "unsupported", "update-available"],
)
def test_status_accepts_every_protocol_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer(state),
    )
    monkeypatch.setenv("DOTBOT_INSTALL_OPERATION", "status")

    assert make_plugin(tmp_path).handle(
        "install", [installer("install/shared/tool.py")]
    )


def test_nonzero_exit_fails_even_with_valid_state(tmp_path: Path) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current", exit_code=9),
    )

    assert not make_plugin(tmp_path).handle(
        "install", [installer("install/shared/tool.py")]
    )


@pytest.mark.parametrize("output", ["", "unknown", "current\ncurrent"])
def test_stdout_must_contain_exactly_one_state(tmp_path: Path, output: str) -> None:
    body = "print({!r}, end='')".format(output)
    write_python_installer(tmp_path, "install/shared/tool.py", body)

    assert not make_plugin(tmp_path).handle(
        "install", [installer("install/shared/tool.py")]
    )


def test_child_receives_shared_environment_without_launcher_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DOTBOT_INSTALL_ONLINE", "0")
    result_file = tmp_path / "result.json"
    body = "\n".join(
        [
            "import json",
            "import os",
            "import sys",
            "from pathlib import Path",
            "result = {",
            "    'args': sys.argv[1:],",
            "    'repo_root': os.environ['DOTBOT_INSTALL_REPO_ROOT'],",
            "    'online': os.environ.get('DOTBOT_INSTALL_ONLINE'),",
            "    'operation': os.environ.get('DOTBOT_INSTALL_OPERATION'),",
            "}",
            "Path({!r}).write_text(json.dumps(result), encoding='utf-8')".format(str(result_file)),
            "print('current')",
        ]
    )
    write_python_installer(tmp_path, "install/shared/tool.py", body)
    assert make_plugin(tmp_path).handle(
        "install",
        [installer(["install/shared/tool.py", "--version", "2.0.0"])],
    )
    result = json.loads(result_file.read_text(encoding="utf-8"))
    assert result == {
        "args": ["--version", "2.0.0", "apply"],
        "repo_root": str(tmp_path.resolve()),
        "online": None,
        "operation": None,
    }
