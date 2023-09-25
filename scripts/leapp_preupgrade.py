import json
import os
import subprocess
import sys


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
        pass
    return None, None


def exit_for_non_eligible_releases(release):
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


def do_rhel7_specific_tasks():
    print("Installing leapp ...")
    output, return_code = run_subprocess(
        [
            "yum",
            "install",
            "leapp-upgrade",
            "-y",
            "--enablerepo=rhel-7-server-extras-rpms",
        ]
    )
    # TODO: Handle error, should we print the output?

    print("Check installed rhui packages for RHEL 7 ...")
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
        {"src_pkg": "google-rhui-client-rhel7", "leapp_pkg": "leapp-rhui-google"},
        {
            "src_pkg": "google-rhui-client-rhel79-sap",
            "leapp_pkg": "leapp-rhui-google-sap",
        },
    ]

    for pkg in rhel_7_rhui_packages:
        if check_if_package_installed(pkg["src_pkg"]):
            pkg["installed"] = True
    return [pkg for pkg in rhel_7_rhui_packages if pkg.get("installed", False)]


def do_rhel8_specific_tasks():
    print("Installing leapp ...")
    output, return_code = run_subprocess(["dnf", "install", "leapp-upgrade", "-y"])
    # TODO: Handle error, should we print the output?

    print("Check installed rhui packages for RHEL 8 ...")
    rhel_8_rhui_packages = [
        {"src_pkg": "rh-amazon-rhui-client", "leapp_pkg": "leapp-rhui-aws"},
        {
            "src_pkg": "rh-amazon-rhui-client-sap-bundle-e4s",
            "leapp_pkg": "leapp-rhui-aws-sap-e4s",
        },
        {"src_pkg": "rhui-azure-rhel8", "leapp_pkg": "leapp-rhui-azure"},
        {"src_pkg": "rhui-azure-rhel8-eus", "leapp_pkg": "leapp-rhui-azure-eus"},
        {"src_pkg": "rhui-azure-rhel8-sap-ha", "leapp_pkg": "leapp-rhui-azure-sap"},
        {"src_pkg": "rhui-azure-rhel8-sapapps", "leapp_pkg": "leapp-rhui-azure-sap"},
        {"src_pkg": "google-rhui-client-rhel8", "leapp_pkg": "leapp-rhui-google"},
        {
            "src_pkg": "google-rhui-client-rhel8-sap",
            "leapp_pkg": "leapp-rhui-google-sap",
        },
    ]
    rhui_installed = False
    for pkg in rhel_8_rhui_packages:
        if check_if_package_installed(pkg["src_pkg"]):
            pkg["installed"] = True
    return [pkg for pkg in rhel_8_rhui_packages if pkg.get("installed", False)]


def should_use_no_rhsm_check(rhui_installed, command):
    print("Checking if subscription manager and repositories are available ...")
    output, rhsm_installed_check = run_subprocess(["which", "subscription-manager"])
    rhsm_installed = rhsm_installed_check == 0
    rhsm_repo_check_fail = True
    if rhsm_installed:
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


def remove_previous_reports():
    print("Removing previous preupgrade reports at /var/log/leapp/leapp-report.* ...")

    json_report_path = "/var/log/leapp/leapp-report.json"
    if os.path.exists(json_report_path):
        os.remove(json_report_path)

    text_report_path = "/var/log/leapp/leapp-report.txt"
    if os.path.exists(text_report_path):
        os.remove(text_report_path)


def execute_preupgrade(command):
    print("Executing preupgrade ...")
    return run_subprocess(command)


def parse_and_output_results():
    print("Processing preupgrade results ...")

    json_report_path = "/var/log/leapp/leapp-report.json"
    report_json = "Not found"
    message = "Can't open json report at " + json_report_path
    alert = True

    print("Reading JSON report")
    if os.path.exists(json_report_path):
        with open(json_report_path, mode="r") as handler:
            report_json = json.load(handler)

        # FIXME: with newer schema we will need to parse groups instead of flags
        report_entries = report_json.get("entries", [])
        inhibitor_count = len(
            [entry for entry in report_entries if "inhibitor" in entry.get("flags")]
        )
        message = "Your system has %s inhibitors out of %s potential problems." % (
            inhibitor_count,
            report_entries,
        )
        alert = inhibitor_count > 0

    print("Reading TXT report")
    text_report_path = "/var/log/leapp/leapp-report.txt"
    report_txt = "Not found"
    if os.path.exists(text_report_path):
        with open(json_report_path, mode="r") as handler:
            report_json = handler.read()

    print("Printing result to stdout")
    results = {
        "report_json": report_json,
        "report": report_txt,
        "message": message,
        "alert": alert,
    }
    print("### JSON START ###")
    print(json.dumps(results, indent=4))
    print("### JSON END ###")


def call_insights_client():
    print("Calling insight-client in background for immediate data collection.")
    return run_subprocess(["insights-client"], wait=False)


def main():
    # Exit if not RHEL 7 or 8
    dist, version = get_rhel_version()
    if dist != "rhel" or exit_for_non_eligible_releases(version):
        print('Exiting because distribution="%s" and version="%s"' % (dist, version))
        sys.exit(1)

    try:
        # Init variables
        preupgrade_command = ["/usr/bin/leapp", "preupgrade", "--report-schema=1.1.0"]
        use_no_rhsm = False
        rhui_pkgs = []

        if version.startswith("7"):
            rhui_pkgs = do_rhel7_specific_tasks()
        elif version.startswith("8"):
            rhui_pkgs = do_rhel8_specific_tasks()
        else:
            print("Exiting, unsupported release", version)
            sys.exit(1)

        use_no_rhsm = should_use_no_rhsm_check(len(rhui_pkgs) > 1, preupgrade_command)
        if use_no_rhsm:
            print("Installing leapp package corresponding to installed rhui packages")
            for pkg in rhui_pkgs:
                run_subprocess(["yum", "install", "-y", pkg["leapp_pkg"]])

        remove_previous_reports()
        output, return_code = execute_preupgrade(preupgrade_command)
        # TODO: Do something with output and return code?

        print("Pre-conversin successfully executed.")
        parse_and_output_results()
        output, return_code = call_insights_client()
        print(output)
        print(return_code)
    except Exception as exception:
        # FIXME: improve this - maybe some general custom exception for errors in all functions
        print("Error occured, exiting ...")
        print(str(exception))


if __name__ == "__main__":
    main()
