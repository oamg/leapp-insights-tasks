from mock import patch
from scripts.leapp_upgrade import (
    main,
    OutputCollector,
    REBOOT_GUIDANCE_MESSAGE,
)


@patch("scripts.leapp_upgrade.get_rhel_version")
@patch("scripts.leapp_upgrade.is_non_eligible_releases")
@patch("scripts.leapp_upgrade.setup_leapp")
@patch("scripts.leapp_upgrade.update_insights_inventory")
@patch("scripts.leapp_upgrade.OutputCollector")
def test_main_non_eligible_release(
    mock_output_collector,
    mock_update_insights_inventory,
    mock_setup_leapp,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
):
    mock_get_rhel_version.return_value = ("rhel", "6.9")
    mock_is_non_eligible_releases.return_value = True
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])

    main()

    mock_get_rhel_version.assert_called_once()
    mock_is_non_eligible_releases.assert_called_once()
    mock_output_collector.assert_called_once()
    mock_setup_leapp.assert_not_called()
    mock_update_insights_inventory.assert_not_called()


@patch("scripts.leapp_upgrade.parse_results")
@patch("scripts.leapp_upgrade.reboot_system")
@patch("scripts.leapp_upgrade.get_rhel_version")
@patch("scripts.leapp_upgrade.is_non_eligible_releases")
@patch("scripts.leapp_upgrade.setup_leapp")
@patch("scripts.leapp_upgrade.should_use_no_rhsm_check")
@patch("scripts.leapp_upgrade.install_leapp_pkg_corresponding_to_installed_rhui")
@patch("scripts.leapp_upgrade.remove_previous_reports")
@patch("scripts.leapp_upgrade.execute_upgrade")
@patch("scripts.leapp_upgrade.update_insights_inventory")
@patch("scripts.leapp_upgrade.OutputCollector")
def test_main_eligible_release(
    mock_output_collector,
    mock_update_insights_inventory,
    mock_execute_upgrade,
    mock_remove_previous_reports,
    mock_should_use_no_rhsm_check,
    mock_install_rhui,
    mock_setup_leapp,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    mock_reboot_system,
    mock_parse_results,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_is_non_eligible_releases.return_value = False
    mock_setup_leapp.return_value = [{"leapp_pkg": "to_install"}]
    mock_should_use_no_rhsm_check.return_value = True
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])
    mock_execute_upgrade.return_value = (
        "LOREM IPSUM\nTEST" + REBOOT_GUIDANCE_MESSAGE + "TEST\nDOLOR SIT AMET"
    )

    main()

    mock_setup_leapp.assert_called_once()
    mock_should_use_no_rhsm_check.assert_called_once()
    mock_install_rhui.assert_called_once()
    mock_remove_previous_reports.assert_called_once()
    mock_execute_upgrade.assert_called_once()
    mock_parse_results.assert_called_once()
    mock_update_insights_inventory.assert_called_once()
    mock_reboot_system.assert_called_once()


@patch("scripts.leapp_upgrade.parse_results")
@patch("scripts.leapp_upgrade.reboot_system")
@patch("scripts.leapp_upgrade.get_rhel_version")
@patch("scripts.leapp_upgrade.is_non_eligible_releases")
@patch("scripts.leapp_upgrade.setup_leapp")
@patch("scripts.leapp_upgrade.should_use_no_rhsm_check")
@patch("scripts.leapp_upgrade.install_leapp_pkg_corresponding_to_installed_rhui")
@patch("scripts.leapp_upgrade.remove_previous_reports")
@patch("scripts.leapp_upgrade.execute_upgrade")
@patch("scripts.leapp_upgrade.update_insights_inventory")
@patch("scripts.leapp_upgrade.OutputCollector")
def test_main_upgrade_not_sucessfull(
    mock_output_collector,
    mock_update_insights_inventory,
    mock_execute_upgrade,
    mock_remove_previous_reports,
    mock_should_use_no_rhsm_check,
    mock_install_rhui,
    mock_setup_leapp,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    mock_reboot_system,
    mock_parse_results,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_is_non_eligible_releases.return_value = False
    mock_setup_leapp.return_value = [{"leapp_pkg": "to_install"}]
    mock_should_use_no_rhsm_check.return_value = True
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])
    mock_execute_upgrade.return_value = "LOREM IPSUM\n" + "\nDOLOR SIT AMET"

    main()

    mock_setup_leapp.assert_called_once()
    mock_should_use_no_rhsm_check.assert_called_once()
    mock_install_rhui.assert_called_once()
    mock_remove_previous_reports.assert_called_once()
    mock_execute_upgrade.assert_called_once()
    mock_parse_results.assert_called_once()
    mock_update_insights_inventory.assert_called_once()
    mock_reboot_system.assert_not_called()
