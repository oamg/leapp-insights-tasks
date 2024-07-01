# Leapp Insights Tasks

Scripts related to [leapp](https://github.com/oamg/leapp) to be run via [rhc-worker-script](https://github.com/oamg/rhc-worker-script) on Red Hat Insights.

Scripts themselves shouldn't have any additional requirements = they are relying on python standard library.

Structure of repository is following:

```txt
├── requirements.txt  # DEV requirements - tests & lint
├── schemas # All expected json outputs in the scripts stdouts
|   |   ...
│   └── preupgrade_schema_1.0.json
├── scripts # All available scripts for leapp related tasks
|   |   ...
│   └── preupgrade_script.py
├── playbooks # All available ansible playbooks for leapp related tasks
|   |   ...
│   └── leapp_preupgrade_ansible.yaml
└── tests
    |   ...
    └── preuprade  # Unit tests for given script
```

## Schemas

Currently there is given format of the scripts stdout that is expected to be parsed by the Red Hat Insights Task UI. This **stdout is JSON structure wrapped between agreed on separators** (see below). Schemas of the JSONs for each script can be found in [schemas](schemas) folder.

* separators (common to all scripts):
    * `### JSON START ###`
    * `### JSON END ###`

## Scripts & Playbooks

Red Hat Insights Tasks are always distributed to registered systems as signed yaml files, those are either executed via [rhc-worker-script](https://github.com/oamg/rhc-worker-script) or [rhc-worker-playbook](https://github.com/RedHatInsights/rhc-worker-playbook). For leapp this generally means that rhc-worker-script is used for RHEL 7 systems and rhc-playbook-worker is used for RHEL 8+ systems.

So in short [playbooks folder](playbooks) contains ansible playbooks and also files from [scripts folder](scripts) wrapped in signed yaml envelope. Beware that the signatures may not be valid, the latest signed playbooks can be downloaded directly in Red Hat Insights Tasks UI, follow [the Tasks official documentation](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/assessing_and_remediating_system_issues_using_red_hat_insights_tasks/overview-tasks).

Only RHEL 8 preupgrade is available in Red Hat Insights production environment.

## Local Development & Contributing

### Requirements

* `python2` - to run tests locally
* `virtualenv` - `versions < 20.22.0` to run tests locally
* `pre-commit` - to run checks before each commit, see hook in [.pre-commit-config.yml](./.pre-commit-config.yaml)
* `make` - to use handy commands

### Run tests and lint

```sh
make install # install pre-commit hooks and python virtualenv
make tests # run pytest
```
