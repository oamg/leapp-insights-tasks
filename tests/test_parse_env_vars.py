import os
import pytest

from scripts.leapp_script import parse_env_vars


@pytest.mark.parametrize(
    ("env", "expected"),
    (
        ({"RHC_WORKER_SCRIPT_MODE": "PREUPGRADE"}, {"SCRIPT_MODE": "PREUPGRADE"}),
        (
            {"RHC_WORKER_FOO": "BAR", "RHC_WORKER_BAR": "FOO"},
            {"FOO": "BAR", "BAR": "FOO"},
        ),
        (
            {"RHC_WORKER_FOO": "BAR", "RHC_BAR": "FOO"},
            {"FOO": "BAR", "RHC_BAR": "FOO"},
        ),
        (
            {"FOO": "BAR", "BAR": "FOO"},
            {"FOO": "BAR", "BAR": "FOO"},
        ),
    ),
)
def test_parse_environment_variables(env, expected, monkeypatch):
    monkeypatch.setattr(os, "environ", env)
    result = parse_env_vars()

    assert result == expected


def test_parse_environment_variables_empty(monkeypatch):
    monkeypatch.setattr(os, "environ", {})
    result = parse_env_vars()
    assert not result