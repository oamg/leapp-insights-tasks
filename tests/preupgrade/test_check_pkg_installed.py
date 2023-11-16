from mock import patch

from scripts.leapp_preupgrade import _check_if_package_installed


@patch("scripts.leapp_preupgrade.run_subprocess")
def test_check_if_package_installed(mock_run_subprocess):
    pkg_name = "example-package"
    mock_run_subprocess.return_value = ("", 0)
    result = _check_if_package_installed(pkg_name)
    expected_command = ["rpm", "-q", pkg_name]
    mock_run_subprocess.assert_called_once_with(expected_command)
    assert result
