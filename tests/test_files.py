"""Tests for the files of an app that the Supervisor confines to its repository."""

from pathlib import Path

from applinter.app import App
from applinter.document import Document
from applinter.rules.files import repository_files, repository_root


def _app(path: Path) -> App:
    """Return an app in a directory, with a configuration that does not matter."""
    path.mkdir(parents=True, exist_ok=True)
    return App(path, Document(path / "config.yaml", {}))


def test_repository_root_is_git(tmp_path: Path) -> None:
    """Test the repository is the closest directory with .git."""
    (tmp_path / ".git").mkdir()
    app = _app(tmp_path / "apps" / "example")

    assert repository_root(app.path) == tmp_path.resolve()


def test_repository_root_without_git(tmp_path: Path) -> None:
    """Test the directory the app is in stands in for a repository without .git."""
    app = _app(tmp_path / "repository" / "example")

    assert repository_root(app.path) == (tmp_path / "repository").resolve()


def test_link_inside_repository(tmp_path: Path) -> None:
    """Test a file linked from another app in the same repository is fine."""
    (tmp_path / ".git").mkdir()
    shared = _app(tmp_path / "shared")
    (shared.path / "icon.png").write_bytes(b"png")
    app = _app(tmp_path / "example")
    (app.path / "icon.png").symlink_to("../shared/icon.png")

    assert not list(repository_files(app))


def test_link_into_git(tmp_path: Path) -> None:
    """Test a file linked into .git, which may hold credentials, is refused."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[remote]")
    app = _app(tmp_path / "example")
    (app.path / "DOCS.md").symlink_to("../.git/config")

    assert [finding.message for finding in repository_files(app)] == [
        "DOCS.md links into .git; the Supervisor refuses it"
    ]


def test_link_loop(tmp_path: Path) -> None:
    """Test a symlink that never resolves is refused, not a crash.

    Made here rather than kept as a fixture: a symlink loop in the
    repository trips up other tools that walk it, such as the cache of
    setup-uv in CI.
    """
    (tmp_path / ".git").mkdir()
    app = _app(tmp_path / "example")
    (app.path / "README.md").symlink_to("README.md")

    assert [finding.message for finding in repository_files(app)] == [
        "README.md is a symlink that never resolves; the Supervisor refuses it"
    ]


def test_link_to_nothing(tmp_path: Path) -> None:
    """Test a symlink to a file that does not exist counts as missing.

    Made here for the same reason as the loop: a dangling symlink is no
    fixture to put in front of every tool that walks the repository.
    """
    (tmp_path / ".git").mkdir()
    app = _app(tmp_path / "example")
    (app.path / "logo.png").symlink_to("missing.png")

    assert [finding.message for finding in repository_files(app)] == [
        (
            "logo.png links to missing.png, which does not exist; the Supervisor "
            "treats it as missing"
        )
    ]
