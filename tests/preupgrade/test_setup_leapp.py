import pytest
from mock import patch
from scripts.leapp_preupgrade import setup_leapp, ProcessError


@pytest.mark.parametrize(
    ("installed"),
    (
        (True),
        (False),
    ),
)
@patch("scripts.leapp_preupgrade.run_subprocess")
@patch("scripts.leapp_preupgrade._check_if_package_installed")
def test_setup_leapp_success(mock_check_if_package_installed, mock_run_subprocess, installed):
    mock_run_subprocess.return_value = ("Installation successful", 0)
    mock_check_if_package_installed.return_value = installed

    rhel7_command = [
        "/usr/bin/yum",
        "install",
        "leapp-upgrade",
        "-y",
        "--enablerepo=rhel-7-server-extras-rpms",
    ]
    rhel8_command = ["/usr/bin/dnf", "install", "leapp-upgrade", "-y"]

    for version, command in [("7", rhel7_command), ("8", rhel8_command)]:
        result = setup_leapp(version)
        if installed:
            assert command not in mock_run_subprocess.call_args_list
        else:
            mock_run_subprocess.assert_called_with(command)
        assert all(pkg.get("installed", False) for pkg in result)


@patch("scripts.leapp_preupgrade.run_subprocess")
@patch("scripts.leapp_preupgrade._check_if_package_installed")
def test_setup_leapp_failure(mock_check_if_package_installed, mock_run_subprocess):
    mock_run_subprocess.return_value = ("Installation failed", 1)
    mock_check_if_package_installed.return_value = False

    rhel7_command = [
        "/usr/bin/yum",
        "install",
        "leapp-upgrade",
        "-y",
        "--enablerepo=rhel-7-server-extras-rpms",
    ]
    rhel8_command = ["/usr/bin/dnf", "install", "leapp-upgrade", "-y"]

    for version, command in [("7", rhel7_command), ("8", rhel8_command)]:
        with pytest.raises(ProcessError) as e_info:
            setup_leapp(version)

        mock_run_subprocess.assert_called_with(command)
        assert (
            str(e_info.value)
            == "Installation of leapp failed with code '1' and output: Installation failed."
        )
