import json
import os
import subprocess


JSON_REPORT_PATH = "/var/log/leapp/leapp-report.json"
TXT_REPORT_PATH = "/var/log/leapp/leapp-report.txt"
REBOOT_GUIDANCE_MESSAGE = "A reboot is required to continue. Please reboot your system."

# Based on https://github.com/oamg/leapp/blob/master/report-schema-v110.json#L211
STATUS_CODE = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}
STATUS_CODE_NAME_MAP = {
    "high": "ERROR",
    "medium": "WARNING",
    "low": "WARNING",
    "info": "INFO",
}


# Both classes taken from:
# https://github.com/oamg/convert2rhel-worker-scripts/blob/main/scripts/preconversion_assessment_script.py
class ProcessError(Exception):
    """Custom exception to report errors during setup and run of leapp"""

    def __init__(self, message, report):
        super(ProcessError, self).__init__(report)
        self.message = message
        self.report = report


class OutputCollector(object):
    """Wrapper class for script expected stdout"""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # Nine and six is reasonable in this case.

    def __init__(
        self, status="", message="", report="", entries=None, alert=False, error=False
    ):
        self.status = status
        self.alert = alert  # true if error true or if pre-upgrade inhibited

        # NOTE: currently false everywhere
        # here for consistency with conversions scripts
        # expected to change after tasks implement new statuses
        self.error = error

        self.message = message
        self.report = report
        self.tasks_format_version = "1.0"
        self.tasks_format_id = "oamg-format"
        self.entries = entries
        self.report_json = None

    def to_dict(self):
        # If we have entries, then we change report_json to be a dictionary
        # with the needed values, otherwise, we leave it as `None` to be
        # transformed to `null` in json.
        if self.entries:
            self.report_json = {
                "tasks_format_version": self.tasks_format_version,
                "tasks_format_id": self.tasks_format_id,
                "entries": self.entries,
            }

        return {
            "status": self.status,
            "alert": self.alert,
            "error": self.error,
            "message": self.message,
            "report": self.report,
            "report_json": self.report_json,
        }


def get_rhel_version():
    """Currently we execute the task only for RHEL 7 or 8"""
    print("Checking OS distribution and version ID ...")
    try:
        distribution_id = None
        version_id = None
        with open("/etc/os-release", "r") as os_release_file:
            for line in os_release_file:
                if line.startswith("ID="):
                    distribution_id = line.split("=")[1].strip().strip('"')
                elif line.startswith("VERSION_ID="):
                    version_id = line.split("=")[1].strip().strip('"')
    except IOError:
        print("Couldn't read /etc/os-release")
    return distribution_id, version_id


def is_non_eligible_releases(release):
    print("Exit if not RHEL 7.9 or 8.4")
    eligible_releases = ["7.9", "8.4"]
    major_version, minor = release.split(".") if release is not None else (None, None)
    version_str = major_version + "." + minor
    return release is None or version_str not in eligible_releases


# Code taken from
# https://github.com/oamg/convert2rhel/blob/v1.4.1/convert2rhel/utils.py#L345
# and modified to adapt the needs of the tools that are being executed in this
# script.
def run_subprocess(cmd, print_cmd=True, env=None, wait=True):
    """
    Call the passed command and optionally log the called command
    (print_cmd=True) and environment variables in form of dictionary(env=None).
    Switching off printing the command can be useful in case it contains a
    password in plain text.

    The cmd is specified as a list starting with the command and followed by a
    list of arguments. Example: ["yum", "install", "<package>"]
    """
    if isinstance(cmd, str):
        raise TypeError("cmd should be a list, not a str")

    if print_cmd:
        print("Calling command '%s'" % " ".join(cmd))

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, env=env
    )

    output = ""

    if not wait:
        return output, None

    for line in iter(process.stdout.readline, b""):
        line = line.decode("utf8")
        output += line

    # Call wait() to wait for the process to terminate so that we can
    # get the return code.
    process.wait()

    return output, process.returncode


def _check_if_package_installed(pkg_name):
    _, return_code = run_subprocess(["/usr/bin/rpm", "-q", pkg_name])
    return return_code == 0


def _get_leapp_command_and_packages(version):
    if version.startswith("7"):
        leapp_install_command = [
            "/usr/bin/yum",
            "install",
            "leapp-upgrade",
            "-y",
            "--enablerepo=rhel-7-server-extras-rpms",
        ]
        rhui_packages = [
            {"src_pkg": "rh-amazon-rhui-client", "leapp_pkg": "leapp-rhui-aws"},
            {
                "src_pkg": "rh-amazon-rhui-client-sap-bundle",
                "leapp_pkg": "leapp-rhui-aws-sap-e4s",
            },
            {"src_pkg": "rhui-azure-rhel7", "leapp_pkg": "leapp-rhui-azure"},
            {
                "src_pkg": "rhui-azure-rhel7-base-sap-apps",
                "leapp_pkg": "leapp-rhui-azure-sap",
            },
            {
                "src_pkg": "rhui-azure-rhel7-base-sap-ha",
                "leapp_pkg": "leapp-rhui-azure-sap",
            },
            {
                "src_pkg": "google-rhui-client-rhel7",
                "leapp_pkg": "leapp-rhui-google",
            },
            {
                "src_pkg": "google-rhui-client-rhel79-sap",
                "leapp_pkg": "leapp-rhui-google-sap",
            },
        ]
    if version.startswith("8"):
        leapp_install_command = ["/usr/bin/dnf", "install", "leapp-upgrade", "-y"]
        rhui_packages = [
            {"src_pkg": "rh-amazon-rhui-client", "leapp_pkg": "leapp-rhui-aws"},
            {
                "src_pkg": "rh-amazon-rhui-client-sap-bundle-e4s",
                "leapp_pkg": "leapp-rhui-aws-sap-e4s",
            },
            {"src_pkg": "rhui-azure-rhel8", "leapp_pkg": "leapp-rhui-azure"},
            {
                "src_pkg": "rhui-azure-rhel8-eus",
                "leapp_pkg": "leapp-rhui-azure-eus",
            },
            {
                "src_pkg": "rhui-azure-rhel8-sap-ha",
                "leapp_pkg": "leapp-rhui-azure-sap",
            },
            {
                "src_pkg": "rhui-azure-rhel8-sapapps",
                "leapp_pkg": "leapp-rhui-azure-sap",
            },
            {
                "src_pkg": "google-rhui-client-rhel8",
                "leapp_pkg": "leapp-rhui-google",
            },
            {
                "src_pkg": "google-rhui-client-rhel8-sap",
                "leapp_pkg": "leapp-rhui-google-sap",
            },
        ]
    return leapp_install_command, rhui_packages


def setup_leapp(version):
    leapp_install_command, rhel_rhui_packages = _get_leapp_command_and_packages(version)
    if _check_if_package_installed('leapp-upgrade'):
        print("'leapp-upgrade' already installed, skipping ...")
    else:
        print("Installing leapp ...")
        output, returncode = run_subprocess(leapp_install_command)
        if returncode:
            raise ProcessError(
                message="Installation of leapp failed",
                report="Installation of leapp failed with code '%s' and output: %s."
                % (returncode, output.rstrip("\n")),
            )

    print("Check installed rhui packages ...")
    for pkg in rhel_rhui_packages:
        if _check_if_package_installed(pkg["src_pkg"]):
            pkg["installed"] = True
    return [pkg for pkg in rhel_rhui_packages if pkg.get("installed", False)]


def should_use_no_rhsm_check(rhui_installed, command):
    print("Checking if subscription manager and repositories are available ...")
    rhsm_repo_check_fail = True
    rhsm_installed_check = _check_if_package_installed("subscription-manager")
    if rhsm_installed_check:
        rhsm_repo_check, _ = run_subprocess(
            ["/usr/sbin/subscription-manager", "repos", "--list-enabled"]
        )
        rhsm_repo_check_fail = (
            "This system has no repositories available through subscriptions."
            in rhsm_repo_check
            or "Repositories disabled by configuration." in rhsm_repo_check
        )

    if rhui_installed and not rhsm_repo_check_fail:
        print("RHUI packages detected, adding --no-rhsm flag to preupgrade command")
        command.append("--no-rhsm")
        return True
    return False


def install_leapp_pkg_corresponding_to_installed_rhui(rhui_pkgs):
    print("Installing leapp package corresponding to installed rhui packages")
    for pkg in rhui_pkgs:
        install_pkg = pkg["leapp_pkg"]
        install_output, returncode = run_subprocess(
            ["/usr/bin/yum", "install", "-y", install_pkg]
        )
        if returncode:
            raise ProcessError(
                message="Installation of %s (coresponding pkg to '%s') failed",
                report="Installation of %s (coresponding pkg to '%s') failed with exit code %s and output: %s."
                % (install_pkg, pkg, returncode, install_output.rstrip("\n")),
            )


def remove_previous_reports():
    print("Removing previous preupgrade reports at /var/log/leapp/leapp-report.* ...")

    if os.path.exists(JSON_REPORT_PATH):
        os.remove(JSON_REPORT_PATH)

    if os.path.exists(TXT_REPORT_PATH):
        os.remove(TXT_REPORT_PATH)


def execute_upgrade(command):
    print("Executing upgrade ...")
    output, _ = run_subprocess(command)

    return output

    # NOTE: we do not care about returncode because non-null always means actor error (or leapp error)
    # if returncode:
    #     print(
    #         "The process leapp exited with code '%s' and output: %s\n"
    #         % (returncode, output)
    #     )
    #     raise ProcessError(message="Leapp exited with code '%s'." % returncode)


def _find_highest_report_level(entries):
    """
    Gather status codes from entries.
    """
    print("Collecting and combining report status.")
    action_level_combined = []
    for value in entries:
        action_level_combined.append(value["severity"])

    valid_action_levels = [
        level for level in action_level_combined if level in STATUS_CODE
    ]
    valid_action_levels.sort(key=lambda status: STATUS_CODE[status], reverse=True)
    return STATUS_CODE_NAME_MAP[valid_action_levels[0]]


def parse_results(output, reboot_required=False):
    print("Processing upgrade results ...")

    report_json = "Not found"
    message = "Can't open json report at " + JSON_REPORT_PATH
    alert = True
    status = "ERROR"

    print("Reading JSON report")
    if os.path.exists(JSON_REPORT_PATH):
        with open(JSON_REPORT_PATH, mode="r") as handler:
            report_json = json.load(handler)

        # NOTE: with newer schema we will need to parse groups instead of flags
        report_entries = report_json.get("entries", [])
        inhibitor_count = len(
            [entry for entry in report_entries if "inhibitor" in entry.get("flags")]
        )
        message = "Your system has %s inhibitors out of %s potential problems." % (
            inhibitor_count,
            len(report_entries),
        )
        if reboot_required:
            message += " System is ready to be upgraded. Rebooting system in 1 minute."
        alert = inhibitor_count > 0
        status = (
            _find_highest_report_level(report_entries)
            if len(report_entries) > 0
            else "SUCCESS"
        )

    output.status = status
    output.report_json = report_json
    output.alert = alert
    output.message = message

    print("Reading TXT report")
    report_txt = "Not found"
    if os.path.exists(TXT_REPORT_PATH):
        with open(JSON_REPORT_PATH, mode="r") as handler:
            report_txt = handler.read()

    output.report = report_txt


def update_insights_inventory():
    """Call insights-client to update insights inventory."""
    print("Updating system status in Red Hat Insights.")
    output, returncode = run_subprocess(["/usr/bin/insights-client"])

    if returncode:
        raise ProcessError(
            message="Failed to update Insights Inventory by registering the system again. See output the following output: %s"
            % output,
            report="insights-client execution exited with code '%s'." % returncode,
        )

    print("System registered with insights-client successfully.")


def reboot_system():
    print("Rebooting system in 1 minute.")
    run_subprocess(["/usr/sbin/shutdown", "-r", "1"], wait=False)


def main():
    try:
        # Exit if not RHEL 7.9 or 8.4
        dist, version = get_rhel_version()
        if dist != "rhel" or is_non_eligible_releases(version):
            raise ProcessError(
                message="In-place upgrades are supported only on RHEL distributions.",
                report='Exiting because distribution="%s" and version="%s"'
                % (dist, version),
            )

        output = OutputCollector()
        upgrade_command = ["/usr/bin/leapp", "upgrade", "--report-schema=1.1.0"]
        rhui_pkgs = setup_leapp(version)

        # Check for RHUI PKGs
        use_no_rhsm = should_use_no_rhsm_check(len(rhui_pkgs) > 1, upgrade_command)
        if use_no_rhsm:
            install_leapp_pkg_corresponding_to_installed_rhui(rhui_pkgs)

        remove_previous_reports()
        leapp_upgrade_output = execute_upgrade(upgrade_command)
        reboot_required = REBOOT_GUIDANCE_MESSAGE in leapp_upgrade_output
        parse_results(output, reboot_required)
        update_insights_inventory()
        print("Leapp upgrade command successfully executed.")
        if reboot_required:
            reboot_system()
    except ProcessError as exception:
        print(exception.report)
        output = OutputCollector(
            status="ERROR",
            alert=True,
            error=False,
            message=exception.message,
            report=exception.report,
        )
    except Exception as exception:
        print(str(exception))
        output = OutputCollector(
            status="ERROR",
            alert=True,
            error=False,
            message="An unexpected error occurred. Expand the row for more details.",
            report=str(exception),
        )
    finally:
        print("### JSON START ###")
        print(json.dumps(output.to_dict(), indent=4))
        print("### JSON END ###")


if __name__ == "__main__":
    main()
