import pytest
from mock import patch, call
from scripts.leapp_preupgrade import (
    ProcessError,
    install_leapp_pkg_corresponding_to_installed_rhui,
)


@patch("scripts.leapp_preupgrade.run_subprocess")
def test_install_leapp_pkg_to_installed_rhui(mock_run_subprocess):
    rhui_pkgs = [{"leapp_pkg": "pkg1"}, {"leapp_pkg": "pkg2"}]

    mock_run_subprocess.return_value = ("Installation successful", 0)

    install_leapp_pkg_corresponding_to_installed_rhui(rhui_pkgs)

    for pkg in rhui_pkgs:
        expected_command = ["yum", "install", "-y", pkg["leapp_pkg"]]
        assert call(expected_command) in mock_run_subprocess.call_args_list


@patch("scripts.leapp_preupgrade.run_subprocess")
def test_install_leapp_pkge_to_installed_rhui_error(
    mock_run_subprocess,
):
    rhui_pkgs = [{"leapp_pkg": "pkg1"}, {"leapp_pkg": "pkg2"}]
    mock_run_subprocess.return_value = ("Installation failed", 1)

    with pytest.raises(ProcessError) as exception:
        install_leapp_pkg_corresponding_to_installed_rhui(rhui_pkgs)

    expected_command = ["yum", "install", "-y", "pkg1"]
    mock_run_subprocess.assert_called_once_with(expected_command)

    assert (
        str(exception.value)
        == "Installation of pkg1 (coresponding pkg to '{'leapp_pkg': 'pkg1'}') failed with exit code 1."
    )
