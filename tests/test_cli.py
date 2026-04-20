from collections.abc import Iterator

import pytest
from click.testing import CliRunner

import pelican.cli as cli_module
from pelican.cli import cli
from pelican.migration import Migration, MigrationRegistry


class _NoopLoader:
    def load_migrations(self) -> None:
        pass


class _EmptyRunner:
    def get_applied_versions(self) -> Iterator[int]:
        return iter([])


class _AppliedRunner:
    def __init__(self, applied: list[int]) -> None:
        self._applied = applied

    def get_applied_versions(self) -> Iterator[int]:
        return iter(self._applied)


class _EmptyRegistry:
    def get(self, revision: int) -> None:
        return None

    def get_all(self) -> list[Migration]:
        return []


def _registry_with(*revisions: int) -> MigrationRegistry:
    r = MigrationRegistry()
    for rev in revisions:
        r.register_up(rev, f"migration_{rev}", lambda: None)
        r.register_down(rev, f"migration_{rev}", lambda: None)
    return r


@pytest.fixture(autouse=True)
def patch_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "loader", _NoopLoader())


def test_down__with_no_applied_migrations__expect_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "runner", _EmptyRunner())
    monkeypatch.setattr(cli_module, "registry", _EmptyRegistry())

    result = CliRunner().invoke(cli, ["down"])

    assert result.exit_code == 0
    assert "No migrations have been applied." in result.output


def test_down__with_unknown_revision__expect_exit_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "runner", _AppliedRunner([1]))
    monkeypatch.setattr(cli_module, "registry", _EmptyRegistry())

    result = CliRunner().invoke(cli, ["down", "99"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_up__with_unknown_revision__expect_exit_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "runner", _EmptyRunner())
    monkeypatch.setattr(cli_module, "registry", _EmptyRegistry())

    result = CliRunner().invoke(cli, ["up", "99"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_up__with_already_applied_revision__expect_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "runner", _AppliedRunner([1]))
    monkeypatch.setattr(cli_module, "registry", _registry_with(1))

    result = CliRunner().invoke(cli, ["up", "1"])

    assert result.exit_code == 0
    assert "already applied" in result.output


def test_status__with_mixed_migrations__expect_correct_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "runner", _AppliedRunner([1]))
    monkeypatch.setattr(cli_module, "registry", _registry_with(1, 2))

    result = CliRunner().invoke(cli, ["status"])

    assert result.exit_code == 0
    assert "✓" in result.output
    assert "○" in result.output
