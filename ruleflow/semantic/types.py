"""Data type definitions and compatibility rules for RuleFlow Compiler."""

from enum import Enum
from typing import Union


class DataType(str, Enum):
    """Enumeration of supported primitive data types in RuleFlow."""

    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    UNKNOWN = "UNKNOWN"

    def is_numeric(self) -> bool:
        """Return True if type is numeric (INTEGER or DECIMAL)."""
        return self in (DataType.INTEGER, DataType.DECIMAL)

    def is_compatible_with(self, other: "DataType") -> bool:
        """Check if a value of type `other` can be assigned/widened to `self`."""
        if self == other:
            return True
        # Widening rule: DECIMAL can accept INTEGER
        if self == DataType.DECIMAL and other == DataType.INTEGER:
            return True
        return False

    @classmethod
    def from_value(cls, val: Union["DataType", str]) -> "DataType":
        """Convert a string or DataType into a normalized DataType member."""
        if isinstance(val, DataType):
            return val
        cleaned = str(val).strip().upper()
        for member in cls:
            if member.value == cleaned:
                return member
        raise ValueError(f"Unknown RuleFlow data type: '{val}'")

    def __str__(self) -> str:
        return self.value
