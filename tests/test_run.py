from mock import patch, ANY

from scripts.leapp_script import execute_operation


@patch("scripts.leapp_script.run_subprocess", return_value=(b"", 0))
def test_execute_simple_command(mock_popen):
    output = execute_operation(["fake command"])

    mock_popen.assert_called_once_with(["fake command"], env=ANY)
    assert output == ""


def test_execure_custom_variables():
    mock_env = {"FOO": "BAR", "BAR": "BAZ", "LALA": "LAND"}
    command = ["/usr/bin/leapp", "preupgrade"]
    with patch("scripts.leapp_script.run_subprocess", return_value=(b"", 0)
    ) as mock_popen:
        result = execute_operation(command, mock_env)
    mock_popen.assert_called_once_with(
        command,
        env={"FOO": "BAR", "BAR": "BAZ", "LALA": "LAND"},
    )
    assert result == ""
