from mock import patch

from scripts.leapp_script import execute_operation


@patch("scripts.leapp_script.run_subprocess", return_value=(b"", 0))
def test_run_leapp_upgrade(mock_popen):
    execute_operation(["fake command"])

    mock_popen.assert_called_once_with(["fake command"])
