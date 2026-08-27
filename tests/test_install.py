import json
from argparse import Namespace
from pathlib import Path
from typing import Dict, Optional

import pytest
from dotbot.context import Context

from install import Install


def make_plugin(repo: Path, dry_run: bool = False) -> Install:
    context = Context(str(repo), Namespace(dry_run=dry_run))
    return Install(context)


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


def test_apply_runs_one_installer_and_accepts_current(tmp_path: Path) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current"),
    )

    assert make_plugin(tmp_path).handle("install", "install/shared/tool.py")


def test_directive_requires_one_scalar_path(tmp_path: Path) -> None:
    assert not make_plugin(tmp_path).handle("install", ["install/shared/tool.py"])


def test_path_must_remain_under_install(tmp_path: Path) -> None:
    write_python_installer(tmp_path, "outside.py", python_installer("current"))

    assert not make_plugin(tmp_path).handle("install", "install/shared/../../outside.py")


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

    assert not make_plugin(tmp_path).handle("install", "install/unix/tool.py")
    assert not marker.exists()


def test_dry_run_does_not_execute_installer(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current", marker=marker),
    )

    assert make_plugin(tmp_path, dry_run=True).handle("install", "install/shared/tool.py")
    assert not marker.exists()


@pytest.mark.parametrize("state", ["absent", "blocked", "drifted"])
def test_apply_requires_a_converged_state(tmp_path: Path, state: str) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer(state),
    )

    assert not make_plugin(tmp_path).handle("install", "install/shared/tool.py")


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

    assert make_plugin(tmp_path).handle("install", "install/shared/tool.py")


def test_nonzero_exit_fails_even_with_valid_state(tmp_path: Path) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current", exit_code=9),
    )

    assert not make_plugin(tmp_path).handle("install", "install/shared/tool.py")


@pytest.mark.parametrize("output", ["", "unknown", "current\ncurrent"])
def test_stdout_must_contain_exactly_one_state(tmp_path: Path, output: str) -> None:
    body = "print({!r}, end='')".format(output)
    write_python_installer(tmp_path, "install/shared/tool.py", body)

    assert not make_plugin(tmp_path).handle("install", "install/shared/tool.py")


def test_upgrade_passes_operation_version_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result_file = tmp_path / "result.json"
    body = "\n".join(
        [
            "import json",
            "import os",
            "import sys",
            "from pathlib import Path",
            "result = {",
            "    'args': sys.argv[1:],",
            "    'id': os.environ['DOTBOT_INSTALL_ID'],",
            "    'operation': os.environ['DOTBOT_INSTALL_OPERATION'],",
            "    'protocol': os.environ['DOTBOT_INSTALL_PROTOCOL_VERSION'],",
            "    'version': os.environ['DOTBOT_INSTALL_VERSION'],",
            "}",
            "Path({!r}).write_text(json.dumps(result), encoding='utf-8')".format(str(result_file)),
            "print('current')",
        ]
    )
    write_python_installer(tmp_path, "install/shared/tool.py", body)
    monkeypatch.setenv("DOTBOT_INSTALL_OPERATION", "upgrade")
    monkeypatch.setenv("DOTBOT_INSTALL_VERSION", "2.0.0")

    assert make_plugin(tmp_path).handle("install", "install/shared/tool.py")
    result: Dict[str, object] = json.loads(result_file.read_text(encoding="utf-8"))
    assert result == {
        "args": ["upgrade", "2.0.0"],
        "id": "install/shared/tool.py",
        "operation": "upgrade",
        "protocol": "1",
        "version": "2.0.0",
    }


def test_version_is_rejected_outside_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_python_installer(
        tmp_path,
        "install/shared/tool.py",
        python_installer("current"),
    )
    monkeypatch.setenv("DOTBOT_INSTALL_VERSION", "2.0.0")

    assert not make_plugin(tmp_path).handle("install", "install/shared/tool.py")
