from scripts.leapp_upgrade import is_non_eligible_releases


def test_is_non_eligible_releases():
    eligible_releases = ["7.9", "8.4"]
    non_eligible_releases = ["6.10", "9.0", "10.0"]

    for release in eligible_releases:
        assert not is_non_eligible_releases(release)

    for release in non_eligible_releases:
        assert is_non_eligible_releases(release)
