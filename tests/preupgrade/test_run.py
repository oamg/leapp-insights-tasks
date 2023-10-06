from mock import patch

from scripts.leapp_preupgrade import execute_preupgrade


@patch("scripts.leapp_preupgrade.run_subprocess", return_value=(b"", 0))
def test_run_leapp_preupgrade(mock_popen):
    execute_preupgrade(["fake command"])

    mock_popen.assert_called_once_with(["fake command"])
