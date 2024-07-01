from mock import patch, Mock, ANY
from scripts.leapp_script import (
    main,
    OutputCollector,
    REBOOT_GUIDANCE_MESSAGE,
)


@patch("scripts.leapp_script.SCRIPT_TYPE", "TEST")
@patch("scripts.leapp_script.setup_sos_report", side_effect=Mock())
@patch("scripts.leapp_script.archive_old_logger_files", side_effect=Mock())
@patch("scripts.leapp_script.setup_logger_handler", side_effect=Mock())
def test_main_invalid_script_type(
    mock_setup_logger_handler,
    mock_setup_sos_report,
    mock_archive_old_logger_files,
    caplog
):
    main()
    log = caplog.text

    assert "Exiting because RHC_WORKER_LEAPP_SCRIPT_TYPE='TEST'" in log

    mock_setup_logger_handler.assert_called_once()
    mock_setup_sos_report.assert_called_once()
    mock_archive_old_logger_files.assert_called_once()


@patch("scripts.leapp_script.SCRIPT_TYPE", "PREUPGRADE")
@patch("scripts.leapp_script.IS_PREUPGRADE", True)
@patch("scripts.leapp_script.get_rhel_version")
@patch("scripts.leapp_script.is_non_eligible_releases")
@patch("scripts.leapp_script.setup_leapp")
@patch("scripts.leapp_script.update_insights_inventory")
@patch("scripts.leapp_script.OutputCollector")
@patch("scripts.leapp_script.setup_sos_report", side_effect=Mock())
@patch("scripts.leapp_script.archive_old_logger_files", side_effect=Mock())
@patch("scripts.leapp_script.setup_logger_handler", side_effect=Mock())
def test_main_non_eligible_release_preupgrade(
    mock_setup_logger_handler,
    mock_setup_sos_report,
    mock_archive_old_logger_files,
    mock_output_collector,
    mock_update_insights_inventory,
    mock_setup_leapp,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    caplog,
):
    mock_get_rhel_version.return_value = ("rhel", "6.9")
    mock_is_non_eligible_releases.return_value = True
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])

    main()

    assert 'Exiting because distribution="rhel" and version="6.9"' in caplog.text

    mock_get_rhel_version.assert_called_once()
    mock_is_non_eligible_releases.assert_called_once()
    mock_output_collector.assert_called_once()
    mock_setup_leapp.assert_not_called()
    mock_update_insights_inventory.assert_not_called()

    mock_setup_logger_handler.assert_called_once()
    mock_setup_sos_report.assert_called_once()
    mock_archive_old_logger_files.assert_called_once()


@patch("scripts.leapp_script.os.environ", {"RHC_WORKER_LEAPP_DEBUG": "true"})
@patch("scripts.leapp_script.SCRIPT_TYPE", "PREUPGRADE")
@patch("scripts.leapp_script.IS_PREUPGRADE", True)
@patch("scripts.leapp_script.parse_results")
@patch("scripts.leapp_script.get_rhel_version")
@patch("scripts.leapp_script.is_non_eligible_releases")
@patch("scripts.leapp_script.setup_leapp")
@patch("scripts.leapp_script.should_use_no_rhsm_check")
@patch("scripts.leapp_script.install_leapp_pkg_corresponding_to_installed_rhui")
@patch("scripts.leapp_script.remove_previous_reports")
@patch("scripts.leapp_script.execute_operation")
@patch("scripts.leapp_script.update_insights_inventory")
@patch("scripts.leapp_script.OutputCollector")
@patch("scripts.leapp_script.setup_sos_report", side_effect=Mock())
@patch("scripts.leapp_script.archive_old_logger_files", side_effect=Mock())
@patch("scripts.leapp_script.setup_logger_handler", side_effect=Mock())
def test_main_eligible_release_preupgrade(
    mock_setup_logger_handler,
    mock_setup_sos_report,
    mock_archive_old_logger_files,
    mock_output_collector,
    mock_update_insights_inventory,
    mock_execute_operation,
    mock_remove_previous_reports,
    mock_should_use_no_rhsm_check,
    mock_install_rhui,
    mock_setup_leapp,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    mock_parse_results,
    caplog,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_is_non_eligible_releases.return_value = False
    mock_setup_leapp.return_value = [{"leapp_pkg": "to_install"}]
    mock_should_use_no_rhsm_check.return_value = True
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])

    main()

    assert "Operation Preupgrade finished successfully." in caplog.text

    mock_setup_leapp.assert_called_once()
    mock_should_use_no_rhsm_check.assert_called_once()
    mock_install_rhui.assert_called_once()
    mock_remove_previous_reports.assert_called_once()
    mock_execute_operation.assert_called_once_with(
        ["/usr/bin/leapp", "preupgrade", "--report-schema=1.2.0"],
        env={"LEAPP_DEBUG": "true"},
    )
    mock_parse_results.assert_called_once()
    mock_update_insights_inventory.assert_called_once()
    mock_setup_logger_handler.assert_called_once()
    mock_setup_sos_report.assert_called_once()
    mock_archive_old_logger_files.assert_called_once()


@patch("scripts.leapp_script.SCRIPT_TYPE", "UPGRADE")
@patch("scripts.leapp_script.IS_UPGRADE", True)
@patch("scripts.leapp_script.parse_results")
@patch("scripts.leapp_script.reboot_system")
@patch("scripts.leapp_script.get_rhel_version")
@patch("scripts.leapp_script.is_non_eligible_releases")
@patch("scripts.leapp_script.setup_leapp")
@patch("scripts.leapp_script.should_use_no_rhsm_check")
@patch("scripts.leapp_script.install_leapp_pkg_corresponding_to_installed_rhui")
@patch("scripts.leapp_script.remove_previous_reports")
@patch("scripts.leapp_script.execute_operation")
@patch("scripts.leapp_script.update_insights_inventory")
@patch("scripts.leapp_script.OutputCollector")
@patch("scripts.leapp_script.setup_sos_report", side_effect=Mock())
@patch("scripts.leapp_script.archive_old_logger_files", side_effect=Mock())
@patch("scripts.leapp_script.setup_logger_handler", side_effect=Mock())
def test_main_eligible_release_upgrade(
    mock_setup_logger_handler,
    mock_setup_sos_report,
    mock_archive_old_logger_files,
    mock_output_collector,
    mock_update_insights_inventory,
    mock_execute_operation,
    mock_remove_previous_reports,
    mock_should_use_no_rhsm_check,
    mock_install_rhui,
    mock_setup_leapp,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    mock_reboot_system,
    mock_parse_results,
    caplog,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_is_non_eligible_releases.return_value = False
    mock_setup_leapp.return_value = [{"leapp_pkg": "to_install"}]
    mock_should_use_no_rhsm_check.return_value = True
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])
    mock_execute_operation.return_value = (
        "LOREM IPSUM\nTEST" + REBOOT_GUIDANCE_MESSAGE + "TEST\nDOLOR SIT AMET"
    )

    main()

    assert "Operation Upgrade finished successfully." in caplog.text

    mock_setup_leapp.assert_called_once()
    mock_should_use_no_rhsm_check.assert_called_once()
    mock_install_rhui.assert_called_once()
    mock_remove_previous_reports.assert_called_once()
    mock_execute_operation.assert_called_once()
    mock_parse_results.assert_called_once()
    mock_update_insights_inventory.assert_called_once()
    # NOTE: reboot_system is currently expected to not be called
    mock_reboot_system.assert_not_called()
    mock_setup_logger_handler.assert_called_once()
    mock_setup_sos_report.assert_called_once()
    mock_archive_old_logger_files.assert_called_once()


@patch("scripts.leapp_script.SCRIPT_TYPE", "UPGRADE")
@patch("scripts.leapp_script.IS_UPGRADE", True)
@patch("scripts.leapp_script.parse_results")
@patch("scripts.leapp_script.reboot_system")
@patch("scripts.leapp_script.get_rhel_version")
@patch("scripts.leapp_script.is_non_eligible_releases")
@patch("scripts.leapp_script.setup_leapp")
@patch("scripts.leapp_script.should_use_no_rhsm_check")
@patch("scripts.leapp_script.install_leapp_pkg_corresponding_to_installed_rhui")
@patch("scripts.leapp_script.remove_previous_reports")
@patch("scripts.leapp_script.execute_operation")
@patch("scripts.leapp_script.update_insights_inventory")
@patch("scripts.leapp_script.OutputCollector")
@patch("scripts.leapp_script.setup_sos_report", side_effect=Mock())
@patch("scripts.leapp_script.archive_old_logger_files", side_effect=Mock())
@patch("scripts.leapp_script.setup_logger_handler", side_effect=Mock())
def test_main_upgrade_not_sucessfull(
    mock_setup_logger_handler,
    mock_setup_sos_report,
    mock_archive_old_logger_files,
    mock_output_collector,
    mock_update_insights_inventory,
    mock_execute_operation,
    mock_remove_previous_reports,
    mock_should_use_no_rhsm_check,
    mock_install_rhui,
    mock_setup_leapp,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    mock_reboot_system,
    mock_parse_results,
    caplog,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_is_non_eligible_releases.return_value = False
    mock_setup_leapp.return_value = [{"leapp_pkg": "to_install"}]
    mock_should_use_no_rhsm_check.return_value = True
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])
    mock_execute_operation.return_value = "LOREM IPSUM\n" + "\nDOLOR SIT AMET"

    main()

    assert "Operation Upgrade finished successfully." in caplog.text

    mock_setup_leapp.assert_called_once()
    mock_should_use_no_rhsm_check.assert_called_once()
    mock_install_rhui.assert_called_once()
    mock_remove_previous_reports.assert_called_once()
    mock_execute_operation.assert_called_once()
    mock_parse_results.assert_called_once()
    mock_update_insights_inventory.assert_called_once()
    mock_reboot_system.assert_not_called()
    mock_setup_logger_handler.assert_called_once()
    mock_setup_sos_report.assert_called_once()
    mock_archive_old_logger_files.assert_called_once()


@patch("scripts.leapp_script.SCRIPT_TYPE", "UPGRADE")
@patch("scripts.leapp_script.IS_UPGRADE", True)
@patch("scripts.leapp_script.parse_results")
@patch("scripts.leapp_script.reboot_system")
@patch("scripts.leapp_script.get_rhel_version")
@patch("scripts.leapp_script.is_non_eligible_releases")
@patch("scripts.leapp_script.should_use_no_rhsm_check")
@patch("scripts.leapp_script.install_leapp_pkg_corresponding_to_installed_rhui")
@patch("scripts.leapp_script.remove_previous_reports")
@patch("scripts.leapp_script.execute_operation")
@patch("scripts.leapp_script.update_insights_inventory")
@patch("scripts.leapp_script.OutputCollector")
@patch("scripts.leapp_script.run_subprocess")
@patch("scripts.leapp_script.setup_sos_report", side_effect=Mock())
@patch("scripts.leapp_script.archive_old_logger_files", side_effect=Mock())
@patch("scripts.leapp_script.setup_logger_handler", side_effect=Mock())
def test_main_setup_leapp_not_sucessfull(
    mock_setup_logger_handler,
    mock_setup_sos_report,
    mock_archive_old_logger_files,
    mock_run_subprocess,
    mock_output_collector,
    mock_update_insights_inventory,
    mock_execute_operation,
    mock_remove_previous_reports,
    mock_should_use_no_rhsm_check,
    mock_install_rhui,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    mock_reboot_system,
    mock_parse_results,
    caplog,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_is_non_eligible_releases.return_value = False
    mock_run_subprocess.return_value = ("Installation failed", 1)
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])

    main()

    assert "Installation of leapp failed with code '1'" in caplog.text

    mock_should_use_no_rhsm_check.assert_not_called()
    mock_install_rhui.assert_not_called()
    mock_remove_previous_reports.assert_not_called()
    mock_execute_operation.assert_not_called()
    mock_parse_results.assert_not_called()
    mock_update_insights_inventory.assert_not_called()
    mock_reboot_system.assert_not_called()
    mock_setup_logger_handler.assert_called_once()
    mock_setup_sos_report.assert_called_once()
    mock_archive_old_logger_files.assert_called_once()


@patch("scripts.leapp_script.SCRIPT_TYPE", "UPGRADE")
@patch("scripts.leapp_script.IS_UPGRADE", True)
@patch("scripts.leapp_script.parse_results")
@patch("scripts.leapp_script.reboot_system")
@patch("scripts.leapp_script.get_rhel_version")
@patch("scripts.leapp_script.is_non_eligible_releases")
@patch("scripts.leapp_script.should_use_no_rhsm_check")
@patch("scripts.leapp_script.setup_leapp")
@patch("scripts.leapp_script.remove_previous_reports")
@patch("scripts.leapp_script.execute_operation")
@patch("scripts.leapp_script.update_insights_inventory")
@patch("scripts.leapp_script.OutputCollector")
@patch("scripts.leapp_script.run_subprocess")
@patch("scripts.leapp_script.setup_sos_report", side_effect=Mock())
@patch("scripts.leapp_script.archive_old_logger_files", side_effect=Mock())
@patch("scripts.leapp_script.setup_logger_handler", side_effect=Mock())
def test_main_install_corresponding_pkgs_not_sucessfull(
    mock_setup_logger_handler,
    mock_setup_sos_report,
    mock_archive_old_logger_files,
    mock_run_subprocess,
    mock_output_collector,
    mock_update_insights_inventory,
    mock_execute_operation,
    mock_remove_previous_reports,
    mock_setup_leapp,
    mock_should_use_no_rhsm_check,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    mock_reboot_system,
    mock_parse_results,
    caplog,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_is_non_eligible_releases.return_value = False
    mock_run_subprocess.return_value = ("Installation failed", 1)
    mock_setup_leapp.return_value = [{"leapp_pkg": "to_install"}]
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])

    main()

    assert (
        "Installation of to_install (coresponding pkg to '{'leapp_pkg': 'to_install'}') failed with exit code 1 and output: Installation failed."
        in caplog.text
    )

    mock_setup_leapp.assert_called_once()
    mock_should_use_no_rhsm_check.assert_called_once()
    mock_remove_previous_reports.assert_not_called()
    mock_execute_operation.assert_not_called()
    mock_parse_results.assert_not_called()
    mock_update_insights_inventory.assert_not_called()
    mock_reboot_system.assert_not_called()
    mock_setup_logger_handler.assert_called_once()
    mock_setup_sos_report.assert_called_once()
    mock_archive_old_logger_files.assert_called_once()


@patch("scripts.leapp_script.SCRIPT_TYPE", "UPGRADE")
@patch("scripts.leapp_script.IS_UPGRADE", True)
@patch("scripts.leapp_script.parse_results")
@patch("scripts.leapp_script.reboot_system")
@patch("scripts.leapp_script.get_rhel_version")
@patch("scripts.leapp_script.is_non_eligible_releases")
@patch("scripts.leapp_script.setup_leapp")
@patch("scripts.leapp_script.should_use_no_rhsm_check")
@patch("scripts.leapp_script.install_leapp_pkg_corresponding_to_installed_rhui")
@patch("scripts.leapp_script.remove_previous_reports")
@patch("scripts.leapp_script.execute_operation")
@patch("scripts.leapp_script.OutputCollector")
@patch("scripts.leapp_script.run_subprocess")
@patch("scripts.leapp_script.setup_sos_report", side_effect=Mock())
@patch("scripts.leapp_script.archive_old_logger_files", side_effect=Mock())
@patch("scripts.leapp_script.setup_logger_handler", side_effect=Mock())
def test_main_update_inventory_not_sucessfull(
    mock_setup_logger_handler,
    mock_setup_sos_report,
    mock_archive_old_logger_files,
    mock_run_subprocess,
    mock_output_collector,
    mock_execute_operation,
    mock_remove_previous_reports,
    mock_should_use_no_rhsm_check,
    mock_install_rhui,
    mock_setup_leapp,
    mock_is_non_eligible_releases,
    mock_get_rhel_version,
    mock_reboot_system,
    mock_parse_results,
    caplog,
):
    mock_get_rhel_version.return_value = ("rhel", "7.9")
    mock_is_non_eligible_releases.return_value = False
    mock_setup_leapp.return_value = [{"leapp_pkg": "to_install"}]
    mock_should_use_no_rhsm_check.return_value = True
    mock_output_collector.return_value = OutputCollector(entries=["non-empty"])
    mock_execute_operation.return_value = "LOREM IPSUM\n" + "\nDOLOR SIT AMET"
    mock_run_subprocess.return_value = ("Installation failed", 1)

    main()
    log = caplog.text
    assert "Updating system status in Red Hat Insights." in log
    assert "System registration failed with exit code 1." in log

    mock_setup_leapp.assert_called_once()
    mock_should_use_no_rhsm_check.assert_called_once()
    mock_install_rhui.assert_called_once()
    mock_remove_previous_reports.assert_called_once()
    mock_execute_operation.assert_called_once()
    mock_parse_results.assert_called_once()
    mock_reboot_system.assert_not_called()
    mock_setup_logger_handler.assert_called_once()
    mock_setup_sos_report.assert_called_once()
    mock_archive_old_logger_files.assert_called_once()
