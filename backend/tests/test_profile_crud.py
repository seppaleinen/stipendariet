"""
Legacy test script for profile CRUD operations.

SKIPPED: This test references Profile.family_members which was removed
during the profile schema redesign. The Profile schema now uses structured
fields (county_code, life_situations, health_conditions, etc.).
"""
import pytest


@pytest.mark.skip(reason="Stale: Profile.family_members no longer exists in schema")
def test_profile_crud():
    pass
