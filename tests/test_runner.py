import os
import signal
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

import runner


@pytest.mark.parametrize(
    "arguments",
    [
        ["--upgrade", "--only", "install", "--dry-run"],
        ["--only", "install", "--upgrade", "--dry-run"],
        ["--only", "install", "--dry-run", "--upgrade"],
    ],
)
def test_upgrade_is_consumed_without_reordering_dotbot_arguments(arguments: list) -> None:
    operation, remaining = runner.parse_lifecycle_arguments(arguments, {})

    assert operation == "upgrade"
    assert remaining == ["--only", "install", "--dry-run"]


def test_no_bridge_and_explicit_bridge_are_equivalent() -> None:
    direct = runner.parse_lifecycle_arguments(["--only", "link", "--upgrade"], {})
    bridged = runner.parse_lifecycle_arguments(["--", "--only", "link", "--upgrade"], {})

    assert direct == bridged == ("upgrade", ["--only", "link"])


def test_unknown_options_and_abbreviations_remain_dotbot_arguments() -> None:
    operation, remaining = runner.parse_lifecycle_arguments(
        ["--up", "--help", "--version"], {}
    )

    assert operation == "apply"
    assert remaining == ["--up", "--help", "--version"]


def test_inherited_status_operation_is_preserved() -> None:
    operation, remaining = runner.parse_lifecycle_arguments(
        ["--only", "install"], {"DOTBOT_INSTALL_OPERATION": "status"}
    )

    assert operation == "status"
    assert remaining == ["--only", "install"]


def test_invalid_inherited_operation_is_rejected() -> None:
    with pytest.raises(runner.LifecycleArgumentError):
        runner.parse_lifecycle_arguments([], {"DOTBOT_INSTALL_OPERATION": "repair"})


def test_run_dotbot_uses_an_argument_array_and_sanitized_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed = subprocess.CompletedProcess([], 7)
    run = Mock(return_value=completed)
    monkeypatch.setattr(runner.subprocess, "run", run)
    environment = {
        "DOTBOT_INSTALL_VERSION": "legacy",
        "DOTBOT_INSTALL_DESIRED_VERSION": "inherited",
        "KEEP": "value",
    }

    result = runner.run_dotbot(
        tmp_path / "dotbot",
        ["--only", "install", "--upgrade"],
        cwd=tmp_path,
        environment=environment,
        python="python-test",
    )

    assert result == 7
    run.assert_called_once_with(
        ["python-test", str(tmp_path / "dotbot"), "--only", "install"],
        cwd=str(tmp_path),
        env={"DOTBOT_INSTALL_OPERATION": "upgrade", "KEEP": "value"},
        check=False,
    )


def test_negative_returncode_is_propagated_as_a_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_signal = Mock()
    kill = Mock()
    monkeypatch.setattr(runner.os, "name", "posix")
    monkeypatch.setattr(runner.signal, "signal", set_signal)
    monkeypatch.setattr(runner.os, "kill", kill)
    monkeypatch.setattr(runner.os, "getpid", lambda: 42)

    assert runner.propagate_returncode(-signal.SIGTERM) == -signal.SIGTERM
    set_signal.assert_called_once_with(signal.SIGTERM, signal.SIG_DFL)
    kill.assert_called_once_with(42, signal.SIGTERM)


def test_main_requires_a_dotbot_path(capsys: pytest.CaptureFixture) -> None:
    assert runner.main([]) == 2
    assert "Expected: <dotbot path>" in capsys.readouterr().err
