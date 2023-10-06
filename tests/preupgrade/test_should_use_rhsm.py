from mock import patch
from scripts.leapp_preupgrade import should_use_no_rhsm_check


@patch("scripts.leapp_preupgrade.run_subprocess")
def test_should_use_no_rhsm_rhsm_and_rhui_installed(
    mock_run_subprocess,
):
    mock_run_subprocess.side_effect = [
        ("/path/to/subscription-manager\n", 0),
        ("output_of_subscription_manager_repos_command", 0),
    ]

    rhui_installed = True
    command = ["preupgrade"]
    result = should_use_no_rhsm_check(rhui_installed, command)

    mock_run_subprocess.call_count = 2
    assert result


@patch("scripts.leapp_preupgrade.run_subprocess")
def test_should_use_no_rhsm_rhsm_installed_rhui_not(
    mock_run_subprocess,
):
    mock_run_subprocess.side_effect = [
        ("/path/to/subscription-manager\n", 0),
        ("output_of_subscription_manager_repos_command", 0),
    ]

    rhui_installed = False
    command = ["preupgrade"]
    result = should_use_no_rhsm_check(rhui_installed, command)

    mock_run_subprocess.call_count = 2
    assert not result


@patch("scripts.leapp_preupgrade.run_subprocess")
def test_should_use_no_rhsm_rhsm_not_installed(mock_run_subprocess):
    mock_run_subprocess.side_effect = [
        ("error_message", 1),
    ]

    rhui_installed = True
    command = ["preupgrade"]
    result = should_use_no_rhsm_check(rhui_installed, command)

    mock_run_subprocess.assert_called_once()
    assert not result
