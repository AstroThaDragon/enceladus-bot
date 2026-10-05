"""Central definitions for station-upgrade identifiers.

The shop transaction remains behaviorally identical; this module provides a
small dependency-light home for upgrade identifiers used by future economy
features and tests.
"""

UPGRADE_IDS = frozenset({"incubator_2", "incubator_3", "vault_expansion"})


def is_station_upgrade(item_type: str | None) -> bool:
    return item_type == "station_upgrade"
