from mock import patch
from scripts.leapp_script import update_insights_inventory, OutputCollector


def test_update_insights_inventory_successfully():
    output = OutputCollector()
    with patch(
        "scripts.leapp_script.run_subprocess", return_value=(b"", 0)
    ) as mock_popen:
        update_insights_inventory(output)
        assert "Failed to update Insights Inventory." not in output.message

    mock_popen.assert_called_once_with(cmd=["/usr/bin/insights-client"])


def test_update_insights_inventory_non_success():
    output = OutputCollector()
    with patch(
        "scripts.leapp_script.run_subprocess", return_value=(b"output", 1)
    ) as mock_popen:
        update_insights_inventory(output)
        assert "Failed to update Insights Inventory." in output.message

    mock_popen.assert_called_once_with(cmd=["/usr/bin/insights-client"])
