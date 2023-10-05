import json
import os
import subprocess


JSON_REPORT_PATH = "/var/log/leapp/leapp-report.json"
TXT_REPORT_PATH = "/var/log/leapp/leapp-report.txt"


# Both classes taken from:
# https://github.com/oamg/convert2rhel-worker-scripts/blob/main/scripts/preconversion_assessment_script.py
class ProcessError(Exception):
    """Custom exception to report errors during setup and run of leapp"""

    def __init__(self, message):
        super(ProcessError, self).__init__(message)
        self.message = message


class OutputCollector(object):
    """Wrapper class for script expected stdout"""

    def __init__(self, status="", message="", report="", entries=None):
        self.status = status
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
            return distribution_id, version_id
    except IOError:
        print("Couldn't read /etc/os-release")
    return None, None


def is_non_eligible_releases(release):
    print("Exit if not RHEL 7 or RHEL 8 ...")
    major_version, _ = release.split(".") if release is not None else (None, None)
    return release is None or major_version not in ["7", "8"]


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


def check_if_package_installed(pkg_name):
    _, return_code = run_subprocess(["rpm", "-q", pkg_name])
    return return_code == 0


def setup_leapp(command, rhui_pkgs):
    print("Installing leapp ...")
    output, returncode = run_subprocess(command)
    if returncode:
        print(
            "Installation of leapp failed with code '%s' and output: %s\n"
            % (returncode, output)
        )
        raise ProcessError(
            message="Installation of leapp failed with code '%s'." % returncode
        )

    print("Check installed rhui packages ...")
    for pkg in rhui_pkgs:
        if check_if_package_installed(pkg["src_pkg"]):
            pkg["installed"] = True
    return [pkg for pkg in rhui_pkgs if pkg.get("installed", False)]


def should_use_no_rhsm_check(rhui_installed, command):
    print("Checking if subscription manager and repositories are available ...")
    rhsm_repo_check_fail = True
    _, rhsm_installed_check = run_subprocess(["which", "subscription-manager"])
    if rhsm_installed_check == 0:
        rhsm_repo_check, _ = run_subprocess(
            ["subscription-manager", "repos", "--list-enabled"]
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
            ["yum", "install", "-y", install_pkg]
        )
        if returncode:
            print("Installation of %s failed. \n%s" % (install_pkg, install_output))
            raise ProcessError(
                message="Installation of %s (coresponding pkg to '%s') failed with exit code %s."
                % (install_pkg, pkg, returncode)
            )


def remove_previous_reports():
    print("Removing previous preupgrade reports at /var/log/leapp/leapp-report.* ...")

    if os.path.exists(JSON_REPORT_PATH):
        os.remove(JSON_REPORT_PATH)

    if os.path.exists(TXT_REPORT_PATH):
        os.remove(TXT_REPORT_PATH)


def execute_preupgrade(command):
    print("Executing preupgrade ...")
    _, _ = run_subprocess(command)

    # NOTE: we do not care about returncode because non-null always means actor error (or leapp error)
    # if returncode:
    #     print(
    #         "The process leapp exited with code '%s' and output: %s\n"
    #         % (returncode, output)
    #     )
    #     raise ProcessError(message="Leapp exited with code '%s'." % returncode)


def parse_results(output):
    print("Processing preupgrade results ...")

    report_json = "Not found"
    message = "Can't open json report at " + JSON_REPORT_PATH
    alert = True

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
        alert = inhibitor_count > 0

    output.report_json = report_json
    output.alert = alert
    output.message = message

    print("Reading TXT report")
    report_txt = "Not found"
    if os.path.exists(TXT_REPORT_PATH):
        with open(JSON_REPORT_PATH, mode="r") as handler:
            report_txt = handler.read()

    output.report = report_txt


def call_insights_client():
    print("Calling insight-client in background for immediate data collection.")
    run_subprocess(["insights-client"], wait=False)
    # NOTE: we do not care about returncode or output because we are not waiting for process to finish


def main():
    # Exit if not RHEL 7 or 8
    dist, version = get_rhel_version()
    if dist != "rhel" or is_non_eligible_releases(version):
        raise ProcessError(
            message='Exiting because distribution="%s" and version="%s"'
            % (dist, version)
        )

    output = OutputCollector()

    try:
        # Init variables
        preupgrade_command = ["/usr/bin/leapp", "preupgrade", "--report-schema=1.1.0"]
        use_no_rhsm = False
        rhui_pkgs = []
        if version.startswith("7"):
            leapp_install_command = [
                "yum",
                "install",
                "leapp-upgrade",
                "-y",
                "--enablerepo=rhel-7-server-extras-rpms",
            ]
            rhel_7_rhui_packages = [
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
            rhui_pkgs = setup_leapp(leapp_install_command, rhel_7_rhui_packages)
        if version.startswith("8"):
            leapp_install_command = ["dnf", "install", "leapp-upgrade", "-y"]
            rhel_8_rhui_packages = [
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
            rhui_pkgs = setup_leapp(leapp_install_command, rhel_8_rhui_packages)

        use_no_rhsm = should_use_no_rhsm_check(len(rhui_pkgs) > 1, preupgrade_command)

        if use_no_rhsm:
            install_leapp_pkg_corresponding_to_installed_rhui(rhui_pkgs)

        remove_previous_reports()
        execute_preupgrade(preupgrade_command)
        print("Pre-upgrade successfully executed.")
    except ProcessError as exception:
        output = OutputCollector(status="ERROR", report=exception.message)
    except Exception as exception:
        output = OutputCollector(status="ERROR", report=str(exception))
    finally:
        parse_results(output)
        print("### JSON START ###")
        print(json.dumps(output.to_dict(), indent=4))
        print("### JSON END ###")
        call_insights_client()


if __name__ == "__main__":
    main()
