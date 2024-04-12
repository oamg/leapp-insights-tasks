import json
import pytest
from mock import mock_open, patch

from scripts.leapp_script import (
    parse_results,
    OutputCollector,
)


@pytest.mark.parametrize(
    ("groups", "severity", "is_upgrade_reboot_needed"),
    (
        (["error"], "high", False),
        (["inhibitor"], "high", False),
        ([], 'info', False),
        (None, None, False), # no entries = success preupgrade
        (None, None, True) # no entries + reboot = success upgrade
    ),
)
@patch("os.path.exists", return_value=True)
def test_gather_report_files_exist(mock_exists, groups, severity, is_upgrade_reboot_needed):
    test_txt_content = "Test data"

    no_entries = groups is None and severity is None
    if no_entries:
        test_json_content = json.dumps({"entries": []})
    else:
        test_json_content = json.dumps({"entries": [{"groups": groups, "severity": severity}]})
    output = OutputCollector()

    with patch("__builtin__.open") as mock_open_reports:
        return_values = [test_json_content, test_txt_content]
        mock_open_reports.side_effect = lambda file, mode: mock_open(
            read_data=return_values.pop(0)
        )(file, mode)
        parse_results(output, is_upgrade_reboot_needed)

    # JSON and TXT report
    assert mock_exists.call_count == 2
    assert output.report == test_txt_content

    if no_entries:
        assert output.status == "SUCCESS"
    else:
        assert output.status == "INFO" if severity == "info" else "ERROR"
        # NOTE: If groups contains error or inhibitor
        # parse_results should replace severity value with 'inhibitor' to distinguish it in UI
        assert output.report_json.get("entries")[0]["severity"] == "info" if severity == "info" else "inhibitor"

    # Message + level
    if severity is None: # no entries in report at all
        if is_upgrade_reboot_needed:
            assert output.message == "No problems found. System will be upgraded. Rebooting system in 1 minute. After reboot check inventory to verify the system is registered with new RHEL major version."
        else:
            assert output.message == "No problems found. The system is ready for upgrade."
        assert output.findings_level == 1
    elif severity != "info":
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
        assert output.findings_level == 7 if "error" in groups else 5
    else: # high, medium, low and info priorities
        # TODO: how about low, medium and high severity? Upgrade can proceed in those cases but should findings level change?
        assert (
            output.message
            == "The upgrade can proceed. However, there is one or more warnings about issues that might occur after the upgrade."
        )
        assert output.findings_level == 1


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

    # TODO: Should it be different when we for some reason can't find the report files?
    assert output.findings_level == 1
