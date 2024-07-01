import json
import pytest
from mock import mock_open, patch

from scripts.leapp_script import (
    parse_results,
    OutputCollector,
)


@pytest.mark.parametrize(
    ("groups_value"),
    (
        ("error"),
        ("inhibitor"),
    ),
)
@patch("os.path.exists", return_value=True)
@patch("scripts.leapp_script._find_highest_report_level", return_value="ERROR")
def test_gather_report_files_exist(mock_find_level, mock_exists, groups_value):
    test_txt_content = "Test data"
    test_json_content = json.dumps({"entries": [{"groups": [groups_value]}]})
    output = OutputCollector()
    with patch("__builtin__.open") as mock_open_reports:
        return_values = [test_json_content, test_txt_content]
        mock_open_reports.side_effect = lambda file, mode: mock_open(
            read_data=return_values.pop(0)
        )(file, mode)
        parse_results(output)

    assert mock_find_level.call_count == 1
    assert output.status == "ERROR"
    assert mock_exists.call_count == 2
    assert output.report == test_txt_content
    assert output.report_json.get("entries") is not None
    assert output.report_json.get("entries")[0]["severity"] == "inhibitor"

    num_errors = test_json_content.count("error")
    num_inhibitor = test_json_content.count("inhibitor")
    inhibitor_str = "%s inhibitor%s" % (
        num_inhibitor + num_errors,
        "" if num_inhibitor + num_errors == 1 else "s",
    )

    assert (
        output.message
        == "The upgrade cannot proceed. Your system has %s out of 1 potential problem."
        % (inhibitor_str,)
    )


@pytest.mark.parametrize(
    ("json_report_mock"),
    (
        ({"entries": []}),  # no problems at all
        ({"entries": [{"groups": [], "severity": "high"}]}),  # no inhibitors
    ),
)
@patch("os.path.exists", return_value=True)
@patch("scripts.leapp_script._find_highest_report_level", return_value="ERROR")
def test_gather_report_files_exist_with_reboot(
    mock_find_level, mock_exists, json_report_mock
):
    test_txt_content = "Test data"
    test_json_content = json.dumps(json_report_mock)
    output = OutputCollector()
    reboot_required = True
    with patch("__builtin__.open") as mock_open_reports:
        return_values = [test_json_content, test_txt_content]
        mock_open_reports.side_effect = lambda file, mode: mock_open(
            read_data=return_values.pop(0)
        )(file, mode)
        parse_results(output, reboot_required)

    mock_entries = json_report_mock.get("entries")
    assert mock_find_level.call_count == len(mock_entries)
    assert output.status == "SUCCESS" if not mock_entries else "ERROR"
    assert mock_exists.call_count == 2
    assert output.report == test_txt_content
    assert output.report_json.get("entries") == mock_entries
    assert (
        output.message
        == "No problems found. Please reboot the system at your earliest convenience to continue with the upgrade process. After reboot check inventory to verify the system is registered with new RHEL major version."
    )


@patch("os.path.exists", return_value=False)
def test_gather_report_files_not_exist(mock_exists):
    output = OutputCollector()
    with patch("__builtin__.open") as mock_open_reports:
        parse_results(output)
        mock_open_reports.assert_not_called()

    assert mock_exists.call_count == 2
    assert output.report != ""
    assert output.report_json != ""
    assert output.message != ""
