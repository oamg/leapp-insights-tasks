from mock import patch

from scripts.leapp_upgrade import call_insights_client


@patch("scripts.leapp_upgrade.run_subprocess", return_value=(b"", 0))
def test_call_insights_client(mock_popen):
    call_insights_client()
    mock_popen.assert_called_once_with(["insights-client"], wait=False)
