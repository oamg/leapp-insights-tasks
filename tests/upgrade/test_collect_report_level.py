import pytest
from scripts.leapp_upgrade import (
    _find_highest_report_level,
)


@pytest.mark.parametrize(
    ("entries", "expected"),
    (
        (
            [
                {
                    "severity": "high",
                },
                {
                    "severity": "info",
                },
            ],
            "ERROR",
        ),
        (
            [
                {
                    "severity": "info",
                }
            ],
            "INFO",
        ),
        (
            [
                {
                    "severity": "medium",
                },
                {
                    "severity": "info",
                },
            ],
            "WARNING",
        ),
    ),
)
def test_find_highest_report_level_expected(entries, expected):
    """Should be sorted descending from the highest status to the lower one."""
    result = _find_highest_report_level(entries)
    assert result == expected


def test_find_highest_report_level_unknown_status():
    """Should ignore unknown statuses in report"""
    expected_output = "WARNING"

    action_results_test = [
        {"severity": "medium"},
        {"severity": "foo"},
    ]
    result = _find_highest_report_level(action_results_test)
    assert result == expected_output
