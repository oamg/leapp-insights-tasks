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
    errors_str = "%s error%s" % (num_errors, "" if num_errors == 1 else "s")
    num_inhibitor = test_json_content.count("inhibitor")
    inhibitor_str = "%s inhibitor%s" % (
        num_inhibitor,
        "" if num_inhibitor == 1 else "s",
    )

    assert output.message == "Your system has %s and %s out of 1 potential problem." % (
        errors_str,
        inhibitor_str,
    )


@patch("os.path.exists", return_value=True)
@patch("scripts.leapp_script._find_highest_report_level", return_value="ERROR")
def test_gather_report_files_exist_with_reboot(mock_find_level, mock_exists):
    test_txt_content = "Test data"
    test_json_content = '{"test": "hi"}'
    output = OutputCollector()
    reboot_required = True
    with patch("__builtin__.open") as mock_open_reports:
        return_values = [test_json_content, test_txt_content]
        mock_open_reports.side_effect = lambda file, mode: mock_open(
            read_data=return_values.pop(0)
        )(file, mode)
        parse_results(output, reboot_required)

    assert mock_find_level.call_count == 0  # entries do not exists -> []
    assert output.status == "SUCCESS"
    assert mock_exists.call_count == 2
    assert output.report == test_txt_content
    assert output.report_json.get("test") == "hi"
    assert (
        output.message
        == "System will be upgraded. Rebooting system in 1 minute. After reboot check inventory to verify the system is registered with new RHEL major version."
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
