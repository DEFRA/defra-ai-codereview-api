"""Tests for ID validation utilities."""
import pytest
from bson import ObjectId
from src.utils.id_validation import ensure_object_id


def test_ensure_object_id_with_valid_string():
    """Test conversion of valid string to ObjectId."""
    id_str = "507f1f77bcf86cd799439011"
    result = ensure_object_id(id_str)
    assert isinstance(result, ObjectId)
    assert str(result) == id_str


def test_ensure_object_id_with_object_id():
    """Test passing ObjectId returns same instance."""
    obj_id = ObjectId()
    result = ensure_object_id(obj_id)
    assert result == obj_id


def test_ensure_object_id_with_none():
    """Test None input returns None."""
    assert ensure_object_id(None) is None


def test_ensure_object_id_with_invalid_string():
    """Test invalid string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid ObjectId format"):
        ensure_object_id("invalid-id")


def test_ensure_object_id_with_invalid_type():
    """Test invalid type raises ValueError."""
    with pytest.raises(ValueError, match="Cannot convert type"):
        ensure_object_id(123)
