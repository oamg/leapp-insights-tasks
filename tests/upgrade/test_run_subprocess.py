# Taken from https://github.com/oamg/convert2rhel-worker-scripts/blob/main/tests/preconversion_assessment/test_misc.py
import subprocess
import pytest
from mock import patch

from scripts.leapp_upgrade import run_subprocess


class SubprocessMock(object):
    def __init__(self, output, returncode):
        self.call_count = 0
        self.output = output
        self.returncode = returncode

    def __call__(self, args, stdout, stderr, bufsize):
        return self

    @property
    def stdout(self):
        return self

    def readline(self):
        try:
            next_line = self.output[self.call_count]
        except IndexError:
            return b""

        self.call_count += 1
        return next_line

    def wait(self):
        pass


def test_run_subprocess_cmd_as_list():
    cmd = "echo 'test'"

    with pytest.raises(TypeError, match="cmd should be a list, not a str"):
        run_subprocess(cmd)


@pytest.mark.parametrize(
    ("subprocess_out", "expected"),
    (
        (("output".encode("utf-8"), 0), ("output", 0)),
        (("output".encode("utf-8"), 1), ("output", 1)),
    ),
)
def test_run_subprocess(subprocess_out, expected):
    with patch(
        "subprocess.Popen",
        return_value=SubprocessMock(subprocess_out[0], subprocess_out[1]),
    ) as mocked_subprocess:
        output, returncode = run_subprocess(["test", "hi"], print_cmd=True)

    assert (output, returncode) == expected
    mocked_subprocess.assert_called_once_with(
        ["test", "hi"],
        bufsize=1,
        env=None,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )


def test_run_subprocess_custom_env():
    with patch(
        "subprocess.Popen", return_value=SubprocessMock("output".encode("utf-8"), 0)
    ) as mocked_subprocess:
        output, returncode = run_subprocess(
            ["test", "hi"], print_cmd=False, env={"PATH": "/fake_path"}
        )

    assert (output, returncode) == ("output", 0)
    mocked_subprocess.assert_called_once_with(
        ["test", "hi"],
        env={"PATH": "/fake_path"},
        bufsize=1,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )


def test_run_subprocess_custom_not_wait():
    with patch(
        "subprocess.Popen", return_value=SubprocessMock("output".encode("utf-8"), 0)
    ) as mocked_subprocess:
        output, returncode = run_subprocess(["test", "hi"], wait=False)

    assert (output, returncode) == ("", None)
    mocked_subprocess.assert_called_once_with(
        ["test", "hi"],
        env=None,
        bufsize=1,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )
