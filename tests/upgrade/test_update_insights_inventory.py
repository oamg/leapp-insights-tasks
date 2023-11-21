import pytest
from mock import patch
from scripts.leapp_upgrade import ProcessError, update_insights_inventory


@patch("scripts.leapp_upgrade.run_subprocess", return_value=(b"", 0))
def test_update_insights_inventory(mock_popen):
    update_insights_inventory()
    mock_popen.assert_called_once_with(["/usr/bin/insights-client"])


@patch("scripts.leapp_upgrade.run_subprocess", return_value=(b"", 1))
def test_update_insights_inventory_error(mock_popen):
    with pytest.raises(ProcessError) as exception:
        update_insights_inventory()
    mock_popen.assert_called_once_with(["/usr/bin/insights-client"])

    assert str(exception.value) == "insights-client execution exited with code '1'."
