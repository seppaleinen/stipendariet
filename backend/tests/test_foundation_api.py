#!/usr/bin/env python3
"""
Test script to verify the foundation API functionality.
Skipped in CI — hits external API (stiftelser.lansstyrelsen.se).
"""
import pytest

from app.foundation.foundation_api import get_foundations_by_query, poll_foundations


@pytest.mark.skip(reason="Hits external API (stiftelser.lansstyrelsen.se) — tested in E2E")
def test_poll_foundations():
    print("Testing poll_foundations()...")
    result = poll_foundations()

    if result:
        print(f"Success! Found {len(result.stiftelser)} foundations")
        if result.stiftelser:
            print(f"First foundation: {result.stiftelser[0].namn}")
            print(f"Updated: {result.uppdaterad}")
        else:
            print("No foundations found in response")
    else:
        print("Failed to get foundations from API")


@pytest.mark.skip(reason="Hits external API (stiftelser.lansstyrelsen.se) — tested in E2E")
def test_search_foundations():
    print("\nTesting get_foundations_by_query('stiftelsen')...")
    result = get_foundations_by_query("stiftelsen")

    if result:
        print(
            f"Success! Found {len(result.stiftelser)} foundations matching 'stiftelsen'"
        )
        if result.stiftelser:
            print(f"First foundation: {result.stiftelser[0].namn}")
        else:
            print("No foundations found matching the query")
    else:
        print("Failed to get foundations from API")


if __name__ == "__main__":
    test_poll_foundations()
    test_search_foundations()
