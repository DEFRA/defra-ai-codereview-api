"""Utilities for ID validation and conversion."""
from typing import Union
from bson import ObjectId
from bson.errors import InvalidId


def ensure_object_id(id_value: Union[str, ObjectId, None]) -> Union[ObjectId, None]:
    """Ensure consistent ObjectId usage.
    
    Args:
        id_value: Value to convert to ObjectId. Can be string, ObjectId, or None.
        
    Returns:
        ObjectId or None if input is None
        
    Raises:
        ValueError: If id_value is invalid
    """
    if id_value is None:
        return None
        
    if isinstance(id_value, ObjectId):
        return id_value
        
    if isinstance(id_value, str):
        try:
            return ObjectId(id_value)
        except InvalidId as e:
            raise ValueError(f"Invalid ObjectId format: {id_value}") from e
            
    raise ValueError(f"Cannot convert type {type(id_value)} to ObjectId")
