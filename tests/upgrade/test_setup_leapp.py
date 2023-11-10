import pytest
from mock import patch
from scripts.leapp_upgrade import setup_leapp, ProcessError


@patch("scripts.leapp_upgrade.run_subprocess")
@patch("scripts.leapp_upgrade.check_if_package_installed")
def test_setup_leapp_success(mock_check_if_package_installed, mock_run_subprocess):
    mock_run_subprocess.return_value = ("Installation successful", 0)
    mock_check_if_package_installed.return_value = True

    command = ["dnf", "install", "leapp-upgrade", "-y"]
    rhui_pkgs = [{"src_pkg": "rh-amazon-rhui-client"}, {"src_pkg": "rhui-azure-rhel8"}]

    result = setup_leapp(command, rhui_pkgs)

    assert mock_check_if_package_installed.call_count == 2
    mock_run_subprocess.assert_called_once_with(command)
    assert all(pkg.get("installed", False) for pkg in result)


@patch("scripts.leapp_upgrade.run_subprocess")
@patch("scripts.leapp_upgrade.check_if_package_installed")
def test_setup_leapp_failure(mock_check_if_package_installed, mock_run_subprocess):
    mock_run_subprocess.return_value = ("Installation failed", 1)
    mock_check_if_package_installed.return_value = True

    command = ["dnf", "install", "leapp-upgrade", "-y"]
    rhui_pkgs = [{"src_pkg": "rh-amazon-rhui-client"}, {"src_pkg": "rhui-azure-rhel8"}]

    with pytest.raises(ProcessError) as e_info:
        setup_leapp(command, rhui_pkgs)

    mock_run_subprocess.assert_called_once_with(command)
    assert mock_check_if_package_installed.call_count == 0
    assert str(e_info.value) == "Installation of leapp failed with code '1'."
