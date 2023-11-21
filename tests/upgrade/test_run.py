from mock import patch

from scripts.leapp_upgrade import execute_upgrade


@patch("scripts.leapp_upgrade.run_subprocess", return_value=(b"", 0))
def test_run_leapp_upgrade(mock_popen):
    execute_upgrade(["fake command"])

    mock_popen.assert_called_once_with(["fake command"])
