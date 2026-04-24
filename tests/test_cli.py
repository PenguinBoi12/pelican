from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import pytest
from click.testing import CliRunner

import pelican.cli as cli_module
from pelican.cli import cli
from pelican.migration import Migration, MigrationRegistry
from pelican._context import _active_runner, _active_registry


class _EmptyRunner:
    has_database_url = True

    def get_applied_versions(self) -> Iterator[int]:
        return iter([])


class _AppliedRunner:
    has_database_url = True

    def __init__(self, applied: list[int]) -> None:
        self._applied = applied

    def get_applied_versions(self) -> Iterator[int]:
        return iter(self._applied)


class _SuccessRunner:
    has_database_url = True

    def __init__(self, applied: list[int] | None = None) -> None:
        self._applied = applied or []

    def get_applied_versions(self) -> Iterator[int]:
        return iter(self._applied)

    def upgrade(self, migration: Migration) -> None:
        pass

    def downgrade(self, migration: Migration) -> None:
        pass


def _registry_with(*revisions: int) -> MigrationRegistry:
    r = MigrationRegistry()
    for rev in revisions:
        r.register_up(rev, f"migration_{rev}", lambda: None)
        r.register_down(rev, f"migration_{rev}", lambda: None)
    return r


def _patch_context(
    monkeypatch: pytest.MonkeyPatch, runner: Any, registry: MigrationRegistry
) -> None:
    @contextmanager
    def fake_use_context(**kwargs: Any) -> Generator[object, Any, None]:
        r_token = _active_runner.set(runner)
        reg_token = _active_registry.set(registry)
        try:
            yield runner
        finally:
            _active_runner.reset(r_token)
            _active_registry.reset(reg_token)

    monkeypatch.setattr(cli_module, "use_context", fake_use_context)


@pytest.fixture(autouse=True)
def patch_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    from pelican._context import get_registry
    from pelican.registry import MigrationRegistry

    class _NoopLoader:
        def load_migrations(self) -> MigrationRegistry:
            return get_registry()

    monkeypatch.setattr(cli_module, "loader", _NoopLoader())


def test_init__expect_directory_and_env_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, ["init"])

    assert result.exit_code == 0
    assert (tmp_path / "db" / "migrations").exists()
    assert (tmp_path / ".env").exists()
    assert "DATABASE_URL" in (tmp_path / ".env").read_text()
    assert "Next steps" in result.output


def test_init__with_existing_project__expect_skip_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "db" / "migrations").mkdir(parents=True)
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql://localhost/mydb\n")

    result = CliRunner().invoke(cli, ["init"])

    assert result.exit_code == 0
    assert "skipping" in result.output
    assert "Next steps" not in result.output
    assert (
        tmp_path / ".env"
    ).read_text() == "DATABASE_URL=postgresql://localhost/mydb\n"


def test_down__with_no_applied_migrations__expect_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_context(monkeypatch, _EmptyRunner(), MigrationRegistry())

    result = CliRunner().invoke(cli, ["down"])

    assert result.exit_code == 0
    assert "No migrations have been applied." in result.output


def test_down__with_unknown_revision__expect_exit_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_context(monkeypatch, _AppliedRunner([1]), MigrationRegistry())

    result = CliRunner().invoke(cli, ["down", "99"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_up__with_unknown_revision__expect_exit_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_context(monkeypatch, _EmptyRunner(), MigrationRegistry())

    result = CliRunner().invoke(cli, ["up", "99"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_up__with_already_applied_revision__expect_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_context(monkeypatch, _AppliedRunner([1]), _registry_with(1))

    result = CliRunner().invoke(cli, ["up", "1"])

    assert result.exit_code == 0
    assert "already applied" in result.output


def test_up__expect_applied_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _SuccessRunner(applied=[]), _registry_with(1))

    result = CliRunner().invoke(cli, ["up"])

    assert result.exit_code == 0
    assert "Applied" in result.output


def test_down__expect_rolled_back_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _SuccessRunner(applied=[1]), _registry_with(1))

    result = CliRunner().invoke(cli, ["down"])

    assert result.exit_code == 0
    assert "Rolled back" in result.output


def test_status__with_mixed_migrations__expect_correct_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_context(monkeypatch, _AppliedRunner([1]), _registry_with(1, 2))

    result = CliRunner().invoke(cli, ["status"])

    assert result.exit_code == 0
    assert "✓" in result.output
    assert "○" in result.output
