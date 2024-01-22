import os
import argparse
import ruamel.yaml

# Scripts located in this project
SCRIPT_PATH = "scripts/leapp_script.py"

REPO_PRE_UPGRADE_YAML_PATH = os.path.join(".", "playbooks/leapp_preupgrade_script.yaml")
REPO_UPGRADE_YAML_PATH = os.path.join(".", "playbooks/leapp_upgrade_script.yaml")

WORKER_PRE_UPGRADE_YAML_PATH = os.path.join(
    "..", "rhc-worker-script/development/nginx/data/leapp_preupgrade.yml"
)
WORKER_UPGRADE_YAML_PATH = os.path.join(
    "..", "rhc-worker-script/development/nginx/data/leapp_upgrade.yml"
)

DEFAULT_YAML_ENVELOPE = """
- name: LEAPP
  vars:
    insights_signature: |
      ascii_armored gpg signature
    insights_signature_exclude: /vars/insights_signature,/vars/content_vars
    interpreter: /usr/bin/python
    content: |
      placeholder
    content_vars:
      # variables that will be handed to the script as environment vars
      # will be prefixed with RHC_WORKER_*
      LEAPP_SCRIPT_TYPE: type
"""


def _get_updated_yaml_content(yaml_path, script_path):
    if not os.path.exists(yaml_path):
        yaml = ruamel.yaml.YAML()
        config = yaml.load(DEFAULT_YAML_ENVELOPE)
        mapping = 2
        offset = 0
    else:
        config, mapping, offset = ruamel.yaml.util.load_yaml_guess_indent(
            open(yaml_path)
        )
        print(mapping, offset)

    with open(script_path) as script:
        content = script.read()

    script_type = "PREUPGRADE" if "preupgrade" in yaml_path else "UPGRADE"
    config[0]["name"] = "Leapp %s for rhc-worker-script" % script_type.title()
    config[0]["vars"]["content"] = content
    config[0]["vars"]["content_vars"]["LEAPP_SCRIPT_TYPE"] = script_type
    return config, mapping, offset


def _write_content(config, path, mapping=None, offset=None):
    yaml = ruamel.yaml.YAML()
    if mapping and offset:
        yaml.indent(mapping=mapping, sequence=mapping, offset=offset)
    with open(path, "w") as handler:
        yaml.dump(config, handler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        choices=["repo", "worker"],
        help="Target to sync scripts to",
        default="worker",
    )
    args = parser.parse_args()

    if args.target == "repo":
        print("Syncing scripts to repo")
        pre_upgrade_path = REPO_PRE_UPGRADE_YAML_PATH
        upgrade_path = REPO_UPGRADE_YAML_PATH

    elif args.target == "worker":
        print("Syncing scripts to worker")
        pre_upgrade_path = WORKER_PRE_UPGRADE_YAML_PATH
        upgrade_path = WORKER_UPGRADE_YAML_PATH

    config, mapping, offset = _get_updated_yaml_content(pre_upgrade_path, SCRIPT_PATH)
    print("Writing new content to %s" % pre_upgrade_path)
    _write_content(config, pre_upgrade_path, mapping, offset)
    config, mapping, offset = _get_updated_yaml_content(upgrade_path, SCRIPT_PATH)
    print("Writing new content to %s" % upgrade_path)
    _write_content(config, upgrade_path, mapping, offset)


if __name__ == "__main__":
    main()
