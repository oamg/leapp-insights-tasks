import pytest
from mock import patch
from scripts.leapp_preupgrade import main, ProcessError, OutputCollector


@patch("scripts.leapp_preupgrade.get_rhel_version")
@patch("scripts.leapp_preupgrade.exit_for_non_eligible_releases")
@patch("scripts.leapp_preupgrade.OutputCollector")
def test_main_non_eligible_release(
    mock_output_collector, mock_exit_for_non_eligible_releases, mock_get_rhel_version
):
    mock_get_rhel_version.return_value = ("rhel", "6.9")
    mock_exit_for_non_eligible_releases.return_value = True

    with pytest.raises(ProcessError):
        main()

    mock_get_rhel_version.assert_called_once()
    mock_exit_for_non_eligible_releases.assert_called_once()
    mock_output_collector.assert_not_called()


@patch("scripts.leapp_preupgrade.parse_results")
@patch("scripts.leapp_preupgrade.get_rhel_version")
@patch("scripts.leapp_preupgrade.exit_for_non_eligible_releases")
@patch("scripts.leapp_preupgrade.setup_leapp")
@patch("scripts.leapp_preupgrade.should_use_no_rhsm_check")
@patch("scripts.leapp_preupgrade.remove_previous_reports")
@patch("scripts.leapp_preupgrade.execute_preupgrade")
@patch("scripts.leapp_preupgrade.run_subprocess")
@patch("scripts.leapp_preupgrade.call_insights_client")
@patch("scripts.leapp_preupgrade.OutputCollector")
def test_main_eligible_release(
    mock_output_collector,
    mock_call_insights_client,
    mock_run_subprocess,
    mock_execute_preupgrade,
    mock_remove_previous_reports,
    mock_should_use_no_rhsm_check,
    mock_setup_leapp,
    mock_exit_for_non_eligible_releases,
    mock_get_rhel_version,
    mock_parse_results,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_exit_for_non_eligible_releases.return_value = False
    mock_setup_leapp.return_value = [{"leapp_pkg": "to_install"}]
    mock_should_use_no_rhsm_check.return_value = True
    mock_run_subprocess.return_value = ("", 0)
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])

    main()

    mock_setup_leapp.assert_called_once()
    mock_should_use_no_rhsm_check.assert_called_once()
    mock_run_subprocess.assert_called_once()
    mock_remove_previous_reports.assert_called_once()
    mock_execute_preupgrade.assert_called_once()
    mock_parse_results.assert_called_once()
    mock_call_insights_client.assert_called_once()
