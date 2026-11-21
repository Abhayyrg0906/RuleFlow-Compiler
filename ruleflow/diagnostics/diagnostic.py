"""Core Diagnostic data structures for RuleFlow Compiler."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class DiagnosticSeverity(Enum):
    """Severity levels for compiler diagnostics."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"

    def __str__(self) -> str:
        return self.value


class DiagnosticCategory(Enum):
    """Compilation pipeline categories for diagnostics."""

    LEXICAL = "LEXICAL"
    SYNTAX = "SYNTAX"
    SEMANTIC = "SEMANTIC"
    OPTIMIZATION = "OPTIMIZATION"
    CODE_GENERATION = "CODE_GENERATION"
    RUNTIME = "RUNTIME"

    def __str__(self) -> str:
        return self.value


@dataclass
class SourceLocation:
    """Represents a specific line and column coordinate in source text."""

    line: int = 1
    column: int = 1

    def __str__(self) -> str:
        return f"Line {self.line}, Column {self.column}"

    def to_dict(self) -> Dict[str, int]:
        return {"line": self.line, "column": self.column}


@dataclass
class SourceRange:
    """Represents a starting and ending position span in source text."""

    start_line: int
    start_column: int
    end_line: int
    end_column: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "start_line": self.start_line,
            "start_column": self.start_column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


class Diagnostic:
    """Represents an individual diagnostic (error, warning, info) produced by the compiler."""

    def __init__(
        self,
        code: str,
        category: DiagnosticCategory,
        severity: DiagnosticSeverity,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        end_line: Optional[int] = None,
        end_column: Optional[int] = None,
        source_line: Optional[str] = None,
        suggestion: Optional[str] = None,
        related_info: Optional[str] = None,
    ):
        self.code = code
        self.category = category
        self.severity = severity
        self.message = message
        self.line = line
        self.column = column
        self.end_line = end_line if end_line is not None else line
        self.end_column = end_column
        self.source_line = source_line
        self.suggestion = suggestion
        self.related_info = related_info

    @property
    def location(self) -> Optional[SourceLocation]:
        """Return SourceLocation if line and column are set."""
        if self.line is not None and self.column is not None:
            return SourceLocation(line=self.line, column=self.column)
        return None

    @property
    def range(self) -> Optional[SourceRange]:
        """Return SourceRange if all coordinates are set."""
        if (
            self.line is not None
            and self.column is not None
            and self.end_line is not None
            and self.end_column is not None
        ):
            return SourceRange(
                start_line=self.line,
                start_column=self.column,
                end_line=self.end_line,
                end_column=self.end_column,
            )
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert diagnostic to dictionary representation."""
        return {
            "code": self.code,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "source_line": self.source_line,
            "suggestion": self.suggestion,
            "related_info": self.related_info,
        }

    def __repr__(self) -> str:
        loc = f" (line {self.line}, col {self.column})" if self.line is not None else ""
        return f"Diagnostic([{self.code}] {self.category.value} {self.severity.value}{loc}: {self.message})"

    def __str__(self) -> str:
        loc = f"Line {self.line}, Column {self.column}: " if self.line is not None and self.column is not None else ""
        return f"[{self.code}] {self.severity.value}: {loc}{self.message}"
