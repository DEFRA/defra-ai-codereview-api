import pytest


def test_resource_cleanup():
    # Simulate an operation that allocates a resource and cleans it up
    resource = {"temp_file": "exists"}

    # Simulate cleanup operation: for this test, cleanup sets the resource to None
    resource["temp_file"] = None

    assert resource["temp_file"] is None, "Resource cleanup failed; temp_file still exists"
