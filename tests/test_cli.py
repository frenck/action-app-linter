"""Tests for the command line, and running as the GitHub Action."""

from pathlib import Path

import pytest

from applinter.cli import main


@pytest.mark.usefixtures("apps")
def test_valid_app(capsys: pytest.CaptureFixture[str]) -> None:
    """Test a valid app passes, and says so."""
    assert main(["valid"]) == 0
    assert capsys.readouterr().out == "No problems found\n"


@pytest.mark.usefixtures("apps")
def test_errors_fail(capsys: pytest.CaptureFixture[str]) -> None:
    """Test errors make the run fail."""
    assert main(["cold-backup"]) == 1
    assert capsys.readouterr().out.endswith("Found 1 error and 0 warnings\n")


@pytest.mark.usefixtures("apps")
def test_warnings_pass(capsys: pytest.CaptureFixture[str]) -> None:
    """Test warnings alone do not make the run fail."""
    assert main(["build", "--ignore", "build-arch-missing,schema"]) == 1
    assert main(["deprecated", "--ignore", "deprecated-auto-uart"]) == 1
    capsys.readouterr()

    assert main(["options", "--ignore", "option-not-in-schema"]) == 0
    assert capsys.readouterr().out.endswith("Found 0 errors and 6 warnings\n")


@pytest.mark.usefixtures("apps")
def test_several_apps(capsys: pytest.CaptureFixture[str]) -> None:
    """Test several apps are linted in one run."""
    assert main(["valid", "cold-backup", "hardware"]) == 1
    output = capsys.readouterr().out
    assert "cold-backup/config.yaml:9" in output
    assert "hardware/config.yaml:9" in output


@pytest.mark.usefixtures("apps")
def test_community(capsys: pytest.CaptureFixture[str]) -> None:
    """Test community mode adds its checks."""
    assert main(["community"]) == 0
    assert main(["community", "--community"]) == 1
    assert "[community-version]" in capsys.readouterr().out


@pytest.mark.usefixtures("apps")
def test_github_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Test annotations are printed when asked for."""
    assert main(["cold-backup", "--format", "github"]) == 1
    output = capsys.readouterr().out
    assert output.startswith(
        "::error file=cold-backup/config.yaml,title=App linter%3A cold-backup-hooks,"
        "line=9::"
    )


@pytest.mark.usefixtures("apps")
def test_github_action(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test the action inputs and annotations, from the environment."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("INPUT_PATH", "./community")
    monkeypatch.setenv("INPUT_COMMUNITY", "true")
    monkeypatch.setenv("INPUT_IGNORE", "community-build-file\n")

    assert main([]) == 1
    output = capsys.readouterr().out.splitlines()
    assert output == [
        (
            "::error file=community/config.yaml,title=App linter%3A community-version,"
            "line=3::'version' is '1.2.3'; community apps use 'dev'"
        ),
        "Found 1 error and 0 warnings",
    ]


@pytest.mark.usefixtures("apps")
def test_current_directory(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test the current directory is linted when no path is given."""
    monkeypatch.chdir(Path("valid"))

    assert main([]) == 0
    assert capsys.readouterr().out == "No problems found\n"


def test_unknown_rule(capsys: pytest.CaptureFixture[str]) -> None:
    """Test ignoring a rule that does not exist is refused."""
    with pytest.raises(SystemExit) as exit_info:
        main(["--ignore", "no-such-rule"])

    assert exit_info.value.code == 2
    assert "unknown rule: no-such-rule" in capsys.readouterr().err


def test_unknown_rule_in_action_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test a typo in the ignore input of the action is a usage error too."""
    monkeypatch.setenv("INPUT_IGNORE", "typo")

    with pytest.raises(SystemExit) as exit_info:
        main([])

    assert exit_info.value.code == 2
    assert "INPUT_IGNORE: unknown rule: typo" in capsys.readouterr().err


@pytest.mark.usefixtures("apps")
def test_ignore_adds_to_action_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test rules ignored on the command line add to the ones of the input."""
    monkeypatch.setenv("INPUT_IGNORE", "full-access")

    assert main(["hardware", "--ignore", "full-access-redundant,default-value"]) == 0
    assert capsys.readouterr().out == "No problems found\n"


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Test the version is shown, read from the package metadata."""
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == "app-linter 0.0.0\n"
