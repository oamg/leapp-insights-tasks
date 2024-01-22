from mock import patch
from scripts.leapp_script import (
    remove_previous_reports,
)


@patch("os.path.exists", side_effect=[True, True])
@patch("os.remove")
def test_remove_previous_reports_with_files(mock_remove, _):
    json_report_path = "/var/log/leapp/leapp-report.json"
    text_report_path = "/var/log/leapp/leapp-report.txt"

    remove_previous_reports()

    mock_remove.assert_any_call(json_report_path)
    mock_remove.assert_any_call(text_report_path)


@patch("os.path.exists", side_effect=[False, False])
@patch("os.remove")
def test_remove_previous_reports_without_files(mock_remove, _):
    remove_previous_reports()
    mock_remove.assert_not_called()
