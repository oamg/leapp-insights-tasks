import pytest
from mock import patch
from scripts.leapp_preupgrade import setup_leapp, ProcessError


@patch("scripts.leapp_preupgrade.run_subprocess")
@patch("scripts.leapp_preupgrade._check_if_package_installed")
def test_setup_leapp_success(mock_check_if_package_installed, mock_run_subprocess):
    mock_run_subprocess.return_value = ("Installation successful", 0)
    mock_check_if_package_installed.return_value = True

    rhel7_command = [
        "yum",
        "install",
        "leapp-upgrade",
        "-y",
        "--enablerepo=rhel-7-server-extras-rpms",
    ]
    rhel8_command = ["dnf", "install", "leapp-upgrade", "-y"]

    for version, command in [("7", rhel7_command), ("8", rhel8_command)]:
        result = setup_leapp(version)
        mock_run_subprocess.assert_called_with(command)
        assert all(pkg.get("installed", False) for pkg in result)


@patch("scripts.leapp_preupgrade.run_subprocess")
@patch("scripts.leapp_preupgrade._check_if_package_installed")
def test_setup_leapp_failure(mock_check_if_package_installed, mock_run_subprocess):
    mock_run_subprocess.return_value = ("Installation failed", 1)
    mock_check_if_package_installed.return_value = True

    rhel7_command = [
        "yum",
        "install",
        "leapp-upgrade",
        "-y",
        "--enablerepo=rhel-7-server-extras-rpms",
    ]
    rhel8_command = ["dnf", "install", "leapp-upgrade", "-y"]

    for version, command in [("7", rhel7_command), ("8", rhel8_command)]:
        with pytest.raises(ProcessError) as e_info:
            setup_leapp(version)

        mock_run_subprocess.assert_called_with(command)
        assert mock_check_if_package_installed.call_count == 0
        assert (
            str(e_info.value)
            == "Installation of leapp failed with code '1' and output: Installation failed."
        )
