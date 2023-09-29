from scripts.leapp_preupgrade import exit_for_non_eligible_releases


def test_exit_for_non_eligible_releases():
    eligible_releases = ["7.9", "8.4"]
    non_eligible_releases = ["6.10", "9.0", "10.0"]

    for release in eligible_releases:
        assert not exit_for_non_eligible_releases(release)

    for release in non_eligible_releases:
        assert exit_for_non_eligible_releases(release)
