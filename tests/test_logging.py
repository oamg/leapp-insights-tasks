import os
import logging
from mock import patch
import pytest
import scripts

from scripts.leapp_script import (
    setup_sos_report,
    setup_logger_handler,
    archive_old_logger_files,
)

def test_setup_sos_report(monkeypatch, tmpdir):
    sos_report_folder = str(tmpdir)
    monkeypatch.setattr(scripts.leapp_script, "SOS_REPORT_FOLDER", sos_report_folder)


    setup_sos_report()

    sos_report_file = os.path.join(
        sos_report_folder, "leapp-insights-tasks-preupgrade-logs"
    )
    assert os.path.exists(sos_report_folder)
    assert os.path.exists(sos_report_file)

    with open(sos_report_file) as handler:
        assert (
            ":/var/log/leapp-insights-tasks/leapp-insights-tasks-preupgrade.log"
            == handler.read().strip()
        )


@patch("scripts.leapp_script.os.makedirs")
@patch("scripts.leapp_script.os.path.exists", side_effect=[False, True])
def test_setup_sos_report_no_sos_report_folder(
    patch_exists, patch_makedirs, monkeypatch, tmpdir
):
    sos_report_folder = str(tmpdir)
    monkeypatch.setattr(scripts.leapp_script, "SOS_REPORT_FOLDER", sos_report_folder)

    setup_sos_report()

    # Folder created
    assert patch_exists.call_count == 2
    patch_makedirs.assert_called_once_with(sos_report_folder)


@patch("scripts.leapp_script.os.makedirs")
@patch("scripts.leapp_script.os.path.exists", side_effect=[False, True])
@patch("scripts.leapp_script.os.getenv", return_value="unknown")
def test_setup_logger_handler(mock_getenv, mock_exist, mock_makedirs, monkeypatch, tmpdir):
    log_dir = str(tmpdir)
    monkeypatch.setattr(scripts.leapp_script, "LOG_DIR", log_dir)
    monkeypatch.setattr(scripts.leapp_script, "LOG_FILENAME", "filelog.log")

    logger = logging.getLogger(__name__)
    setup_logger_handler()

    # emitting some log entries
    logger.info("Test info: %s", "data")
    logger.debug("Test debug: %s", "other data")

    mock_getenv.assert_called_once_with("RHC_WORKER_LOG_LEVEL", "INFO")
    mock_exist.assert_called_once_with(log_dir)
    mock_makedirs.assert_called_once_with(log_dir)


def test_archive_old_logger_files(monkeypatch, tmpdir):
    log_dir = str(tmpdir)
    archive_dir = os.path.join(log_dir, "archive")
    monkeypatch.setattr(scripts.leapp_script, "LOG_DIR", log_dir)
    monkeypatch.setattr(scripts.leapp_script, "LOG_FILENAME", "test.log")

    original_log_file = tmpdir.join("test.log")
    original_log_file.write("test")

    archive_old_logger_files()

    assert os.path.exists(log_dir)
    assert os.path.exists(archive_dir)
    assert len(os.listdir(archive_dir)) == 1


def test_archive_old_logger_files_no_log_file(monkeypatch, tmpdir):
    log_dir = str(tmpdir.join("something-else"))
    monkeypatch.setattr(scripts.leapp_script, "LOG_DIR", log_dir)
    monkeypatch.setattr(scripts.leapp_script, "LOG_FILENAME", "test.log")

    archive_old_logger_files()

    assert not os.path.exists(log_dir)