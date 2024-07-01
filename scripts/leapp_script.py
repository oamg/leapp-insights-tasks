import json
import logging
import os
import shutil
import sys
import subprocess

from time import gmtime, strftime


# SCRIPT_TYPE is either 'PREUPGRADE' or 'UPGRADE'
# Value is set in signed yaml envelope in content_vars (RHC_WORKER_LEAPP_SCRIPT_TYPE)
SCRIPT_TYPE = os.environ.get("RHC_WORKER_LEAPP_SCRIPT_TYPE", "None")
IS_UPGRADE = SCRIPT_TYPE == "UPGRADE"
IS_PREUPGRADE = SCRIPT_TYPE == "PREUPGRADE"
JSON_REPORT_PATH = "/var/log/leapp/leapp-report.json"
TXT_REPORT_PATH = "/var/log/leapp/leapp-report.txt"
REBOOT_GUIDANCE_MESSAGE = "A reboot is required to continue. Please reboot your system."

ALLOWED_RHEL_RELEASES = ["7", "8"]

# Based on https://github.com/oamg/leapp/blob/master/report-schema-v110.json#L211
STATUS_CODE = {
    "inhibitor": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}
STATUS_CODE_NAME_MAP = {
    "inhibitor": "ERROR",
    "high": "ERROR",
    "medium": "WARNING",
    "low": "WARNING",
    "info": "INFO",
}


# Path to store the script logs
LOG_DIR = "/var/log/leapp-insights-tasks"
# Log filename for the script. It will be created based on the script type of
# execution.
LOG_FILENAME = "leapp-insights-tasks-%s.log" % (
    "upgrade" if IS_UPGRADE else "preupgrade"
)

# Path to the sos extras folder
SOS_REPORT_FOLDER = "/etc/sos.extras.d"
# Name of the file based on the task type for sos report
SOS_REPORT_FILE = "leapp-insights-tasks-%s-logs" % (
    "upgrade" if IS_UPGRADE else "preupgrade"
)

logger = logging.getLogger(__name__)


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


def setup_sos_report():
    """Setup sos report log collection."""
    if not os.path.exists(SOS_REPORT_FOLDER):
        os.makedirs(SOS_REPORT_FOLDER)

    script_log_file = os.path.join(LOG_DIR, LOG_FILENAME)
    sosreport_link_file = os.path.join(SOS_REPORT_FOLDER, SOS_REPORT_FILE)
    # In case the file for sos report does not exist, lets create one and add
    # the log file path to it.
    if not os.path.exists(sosreport_link_file):
        with open(sosreport_link_file, mode="w") as handler:
            handler.write(":%s\n" % script_log_file)


def setup_logger_handler():
    """
    Setup custom logging levels, handlers, and so on. Call this method from
    your application's main start point.
    """
    # Receive the log level from the worker and try to parse it. If the log
    # level is not compatible with what the logging library expects, set the
    # log level to INFO automatically.
    log_level = os.getenv("RHC_WORKER_LOG_LEVEL", "INFO").upper()
    log_level = logging.getLevelName(log_level)
    if isinstance(log_level, str):
        log_level = logging.INFO

    # enable raising exceptions
    logging.raiseExceptions = True
    logger.setLevel(log_level)

    # create sys.stdout handler for info/debug
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    stdout_handler.setFormatter(formatter)

    # Create the directory if it don't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    log_filepath = os.path.join(LOG_DIR, LOG_FILENAME)
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setFormatter(formatter)

    # can flush logs to the file that were logged before initializing the file handler
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)


def archive_old_logger_files():
    """
    Archive the old log files to not mess with multiple runs outputs. Every
    time a new run begins, this method will be called to archive the previous
    logs if there is a `convert2rhel.log` file there, it will be archived using
    the same name for the log file, but having an appended timestamp to it.
    For example:
        /var/log/leapp-insights-tasks/archive/leapp-insights-tasks-1635162445070567607.log
        /var/log/leapp-insights-tasks/archive/leapp-insights-tasks-1635162478219820043.log
    This way, the user can track the logs for each run individually based on
    the timestamp.
    """

    current_log_file = os.path.join(LOG_DIR, LOG_FILENAME)
    archive_log_dir = os.path.join(LOG_DIR, "archive")

    # No log file found, that means it's a first run or it was manually deleted
    if not os.path.exists(current_log_file):
        return

    stat = os.stat(current_log_file)

    # Get the last modified time in UTC
    last_modified_at = gmtime(stat.st_mtime)

    # Format time to a human-readable format
    formatted_time = strftime("%Y%m%dT%H%M%SZ", last_modified_at)

    # Create the directory if it don't exist
    if not os.path.exists(archive_log_dir):
        os.makedirs(archive_log_dir)

    file_name, suffix = tuple(LOG_FILENAME.rsplit(".", 1))
    archive_log_file = "%s/%s-%s.%s" % (
        archive_log_dir,
        file_name,
        formatted_time,
        suffix,
    )
    shutil.move(current_log_file, archive_log_file)


def get_rhel_version():
    """Currently we execute the task only for RHEL 7 or 8"""
    logger.info("Checking OS distribution and version ID ...")
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
        logger.warn("Couldn't read /etc/os-release")
    return distribution_id, version_id


def is_non_eligible_releases(release):
    """Check if the release is eligible for upgrade or preupgrade."""
    logger.info("Exit if not RHEL 7 or RHEL 8 ...")
    major_version, _ = release.split(".") if release is not None else (None, None)
    return release is None or major_version not in ALLOWED_RHEL_RELEASES


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
        logger.info("Calling command '%s'", " ".join(cmd))

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
    if _check_if_package_installed("leapp-upgrade"):
        logger.info("'leapp-upgrade' already installed, skipping ...")
    else:
        logger.info("Installing leapp ...")
        output, returncode = run_subprocess(leapp_install_command)
        if returncode:
            raise ProcessError(
                message="Installation of leapp failed",
                report="Installation of leapp failed with code '%s' and output: %s."
                % (returncode, output.rstrip("\n")),
            )

    logger.info("Check installed rhui packages ...")
    for pkg in rhel_rhui_packages:
        if _check_if_package_installed(pkg["src_pkg"]):
            pkg["installed"] = True
    return [pkg for pkg in rhel_rhui_packages if pkg.get("installed", False)]


def should_use_no_rhsm_check(rhui_installed, command):
    logger.info("Checking if subscription manager and repositories are available ...")
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
        logger.info(
            "RHUI packages detected, adding --no-rhsm flag to % command",
            SCRIPT_TYPE.title()
        )
        command.append("--no-rhsm")
        return True
    return False


def install_leapp_pkg_corresponding_to_installed_rhui(rhui_pkgs):
    logger.info("Installing leapp package corresponding to installed rhui packages")
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
    logger.info("Removing previous leapp reports at /var/log/leapp/leapp-report.* ...")

    if os.path.exists(JSON_REPORT_PATH):
        os.remove(JSON_REPORT_PATH)

    if os.path.exists(TXT_REPORT_PATH):
        os.remove(TXT_REPORT_PATH)


def parse_env_vars():
    new_env = {}
    for key, value in os.environ.items():
        valid_prefix = "RHC_WORKER_"
        if key.startswith(valid_prefix):
            # This also removes multiple valid prefixes
            new_env[key.replace(valid_prefix, "")] = value
        else:
            new_env[key] = value
    return new_env


def execute_operation(command, env=None):
    # NOTE: Put logic here to adjust command based on environment variables
    # if "LEAPP_DEBUG" in env:
    #     command.append("--debug")
    # if "LEAPP_NO_RHSM" in env:
    #     command.append("--no-rhsm")
    # if "LEAPP_ENABLE_REPOS" in env:
    #     command.extend([["--enablerepo", repo] for repo in env["LEAPP_ENABLE_REPOS"].split(",")])

    logger.info("Executing %s ...", SCRIPT_TYPE.title())
    output, _ = run_subprocess(command, env=env)

    return output


def _find_highest_report_level(entries):
    """
    Gather status codes from entries.
    """
    logger.info("Collecting and combining report status.")
    action_level_combined = [value["severity"] for value in entries]

    valid_action_levels = [
        level for level in action_level_combined if level in STATUS_CODE
    ]
    valid_action_levels.sort(key=lambda status: STATUS_CODE[status], reverse=True)
    return STATUS_CODE_NAME_MAP[valid_action_levels[0]]


def parse_results(output, reboot_required=False):
    logger.info("Processing %s results ...", SCRIPT_TYPE.title())

    report_json = "Not found"
    message = "Can't open json report at " + JSON_REPORT_PATH
    alert = True
    status = "ERROR"

    logger.info("Reading JSON report")
    if os.path.exists(JSON_REPORT_PATH):
        with open(JSON_REPORT_PATH, mode="r") as handler:
            report_json = json.load(handler)

        report_entries = report_json.get("entries", [])
        for entry in report_entries:
            groups = entry.get("groups", [])
            # NOTE: "severity" key in report is connected to tasks-frontend severity maps
            # Every change must come with change to severity maps otherwise UI will throw sentry errors
            if "error" in groups:
                entry["severity"] = "inhibitor"
            elif "inhibitor" in groups:
                entry["severity"] = "inhibitor"

        total_problems_count = len(report_entries)
        error_count = len(
            [entry for entry in report_entries if "error" in entry.get("groups")]
        )
        inhibitor_count = len(
            [entry for entry in report_entries if "inhibitor" in entry.get("groups")]
        )

        if inhibitor_count == 0 and error_count == 0:
            if total_problems_count == 0:
                message = "No problems found. The system is ready for upgrade."
            else:
                message = "The upgrade can proceed. However, there is one or more warnings about issues that might occur after the upgrade."
        else:
            message = (
                "The upgrade cannot proceed. "
                "Your system has %s inhibitor%s out of %s potential problem%s."
                % (
                    inhibitor_count + error_count,
                    "" if inhibitor_count + error_count == 1 else "s",
                    len(report_entries),
                    "" if len(report_entries) == 1 else "s",
                )
            )

        if reboot_required:
            message = (
                "No problems found. Please reboot the system at your earliest convenience "
                "to continue with the upgrade process. "
                "After reboot check inventory to verify the system is registered with new RHEL major version."
            )
        alert = inhibitor_count > 0 or error_count > 0
        status = (
            _find_highest_report_level(report_entries)
            if len(report_entries) > 0
            else "SUCCESS"
        )

    output.status = status
    output.report_json = report_json
    output.alert = alert
    output.message = message

    logger.info("Reading TXT report")
    report_txt = "Not found"
    if os.path.exists(TXT_REPORT_PATH):
        with open(TXT_REPORT_PATH, mode="r") as handler:
            report_txt = handler.read()

    output.report = report_txt


def update_insights_inventory(output):
    """Call insights-client to update insights inventory."""
    logger.info("Updating system status in Red Hat Insights.")
    _, returncode = run_subprocess(cmd=["/usr/bin/insights-client"])

    if returncode:
        logger.info("System registration failed with exit code %s.", returncode)
        output.message += " Failed to update Insights Inventory."
        output.alert = True
        return

    logger.info("System registered with insights-client successfully.")


def reboot_system():
    logger.info("Rebooting system in 1 minute.")
    run_subprocess(["/usr/sbin/shutdown", "-r", "1"], wait=False)


def main():
    """Main entrypoint for the script."""
    setup_sos_report()
    archive_old_logger_files()
    setup_logger_handler()
    try:
        # Exit if invalid value for SCRIPT_TYPE
        if SCRIPT_TYPE not in ["PREUPGRADE", "UPGRADE"]:
            raise ProcessError(
                message="Allowed values for RHC_WORKER_LEAPP_SCRIPT_TYPE are 'PREUPGRADE' and 'UPGRADE'.",
                report="Exiting because RHC_WORKER_LEAPP_SCRIPT_TYPE='%s'"
                % SCRIPT_TYPE,
            )

        # Exit if not eligible release
        dist, version = get_rhel_version()
        if dist != "rhel" or is_non_eligible_releases(version):
            message = "In-place upgrades are supported only on RHEL %s." % ",".join(
                ALLOWED_RHEL_RELEASES
            )
            raise ProcessError(
                message=message,
                report='Exiting because distribution="%s" and version="%s"'
                % (dist, version),
            )

        output = OutputCollector()
        preupgrade_command = ["/usr/bin/leapp", "preupgrade", "--report-schema=1.2.0"]
        upgrade_command = ["/usr/bin/leapp", "upgrade", "--report-schema=1.2.0"]
        operation_command = preupgrade_command if IS_PREUPGRADE else upgrade_command
        rhui_pkgs = setup_leapp(version)

        # Check for RHUI PKGs
        use_no_rhsm = should_use_no_rhsm_check(len(rhui_pkgs) > 1, operation_command)
        if use_no_rhsm:
            install_leapp_pkg_corresponding_to_installed_rhui(rhui_pkgs)

        remove_previous_reports()

        # NOTE: adjust commands based on parameters in environment variables
        env = parse_env_vars()
        leapp_output = execute_operation(operation_command, env=env)
        upgrade_reboot_required = REBOOT_GUIDANCE_MESSAGE in leapp_output
        parse_results(output, upgrade_reboot_required)
        update_insights_inventory(output)
        logger.info("Operation %s finished successfully.", SCRIPT_TYPE.title())

        # NOTE: Leapp has --reboot option but we are not using it because we need to send update to Insights before reboot
        # if upgrade_reboot_required:
        #     reboot_system()
    except ProcessError as exception:
        logger.error(exception.report)
        output = OutputCollector(
            status="ERROR",
            alert=True,
            error=False,
            message=exception.message,
            report=exception.report,
        )
    except Exception as exception:
        logger.critical(str(exception))
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
