"""Semantic error exception definitions for RuleFlow Compiler."""

from typing import Optional


class SemanticError(Exception):
    """Exception raised when semantic validation, scope resolution, or type checking fails."""

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        identifier: Optional[str] = None,
        operator: Optional[str] = None,
    ):
        self.message = message
        self.line = line
        self.column = column
        self.identifier = identifier
        self.operator = operator

        location = ""
        if line is not None and column is not None:
            location = f"[Line {line}, Col {column}] "
        elif line is not None:
            location = f"[Line {line}] "

        super().__init__(f"{location}Semantic Error: {message}")
