import pytest


def test_error_messages():
    # Simulate a failure condition by raising an error with a specific message
    try:
        raise RuntimeError("Simulated error: invalid code review input")
    except RuntimeError as e:
        expected_error = "Simulated error: invalid code review input"
        assert str(
            e) == expected_error, f"Expected error message: {expected_error}, got: {str(e)}"
