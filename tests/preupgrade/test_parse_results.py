from mock import mock_open, patch

from scripts.leapp_preupgrade import (
    parse_results,
    OutputCollector,
)


@patch("os.path.exists", return_value=True)
@patch("scripts.leapp_preupgrade.find_highest_report_level", return_value="ERROR")
def test_gather_report_files_exist(mock_find_level, mock_exists):
    test_txt_content = "Test data"
    test_json_content = '{"test": "hi"}'
    output = OutputCollector()
    with patch("__builtin__.open") as mock_open_reports:
        return_values = [test_json_content, test_txt_content]
        mock_open_reports.side_effect = lambda file, mode: mock_open(
            read_data=return_values.pop(0)
        )(file, mode)
        parse_results(output)

    assert mock_find_level.call_count == 0  # entries do not exists -> []
    assert output.status == "SUCCESS"
    assert mock_exists.call_count == 2
    assert output.report == test_txt_content
    assert output.report_json.get("test") == "hi"
    # NOTE: is this right?
    assert output.message == "Your system has 0 inhibitors out of 0 potential problems."


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
