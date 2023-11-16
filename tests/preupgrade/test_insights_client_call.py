from mock import patch

from scripts.leapp_preupgrade import call_insights_client


@patch("scripts.leapp_preupgrade.run_subprocess", return_value=(b"", 0))
def test_call_insights_client(mock_popen):
    call_insights_client()
    mock_popen.assert_called_once_with(["/usr/bin/insights-client"], wait=False)
