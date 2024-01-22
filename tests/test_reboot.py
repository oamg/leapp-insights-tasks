from mock import patch

from scripts.leapp_script import reboot_system


@patch("scripts.leapp_script.run_subprocess", return_value=(b"", 0))
def test_reboot(mock_popen):
    reboot_system()
    mock_popen.assert_called_once_with(["/usr/sbin/shutdown", "-r", "1"], wait=False)
