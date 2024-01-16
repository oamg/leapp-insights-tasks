"""
This file serves to be run during a pre-commit hook to wrap all scripts/ files
in yaml and convert them to ansible playbooks placed under playbooks/ folder.
"""

import re
import sys
from pathlib import Path


def wrap_script_in_yaml(python_file):
    yaml_file_path = f"playbooks/{Path(python_file).stem}_script.yaml"
    yaml_content = generate_yaml_content(python_file)

    if not Path(yaml_file_path).exists() or open(yaml_file_path).read() != yaml_content:
        with open(yaml_file_path, "w") as yaml_file:
            yaml_file.write(yaml_content)
        return True
    return False


def generate_yaml_content(python_file):
    with open(python_file, "r") as py_file:
        content = ""
        if python_file == "scripts/leapp_preupgrade.py":
            content += "- name: Leapp pre-upgrade for rhc-worker-script\n"
        elif python_file == "scripts/leapp_upgrade.py":
            content += "- name: Leapp upgrade for rhc-worker-script\n"
        content += "  vars:\n"
        content += "    insights_signature: !!binary |\n"
        content += "      needs signature\n"
        content += '    insights_signature_exclude: "/vars/insights_signature"\n'
        content += "    interpreter: /usr/bin/python\n"
        content += "    content: |\n"
        for line in py_file:
            if not line.strip():
                # Do not indent empty lines, causes errors with other pre-commit hooks
                content += line
            else:
                content += f"      {line}"
        content += "    content_vars:\n"
        return content


def main():
    changes_detected = False
    for filename in sys.argv[1:]:
        if re.match(r"scripts/.*.py$", filename):
            if filename == f"scripts/{Path(__file__).name}":
                continue
            if wrap_script_in_yaml(filename):
                changes_detected = True

    if changes_detected:
        print(
            "Changes detected in ansible playbooks (coming from scripts). Please stage them and commit again."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
