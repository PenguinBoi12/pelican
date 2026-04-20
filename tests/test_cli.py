import pytest
from click.testing import CliRunner

import pelican.cli as cli_module
from pelican.cli import cli


class _EmptyRunner:
    def get_applied_versions(self):
        return iter([])


class _NoopLoader:
    def load_migrations(self):
        pass


class _EmptyRegistry:
    pass


@pytest.fixture(autouse=True)
def patch_cli(monkeypatch):
    monkeypatch.setattr(cli_module, "runner", _EmptyRunner())
    monkeypatch.setattr(cli_module, "loader", _NoopLoader())
    monkeypatch.setattr(cli_module, "registry", _EmptyRegistry())


def test_down__with_no_applied_migrations__expect_message():
    result = CliRunner().invoke(cli, ["down"])
    assert result.exit_code == 0
    assert "No migrations have been applied." in result.output
