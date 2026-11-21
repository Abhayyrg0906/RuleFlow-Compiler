"""RuleFlow Diagnostics package.

Provides structured, compiler-wide error diagnostics, source location tracking,
code snippet highlighting with caret indicators, and intelligent typo suggestions.
"""

from .codes import DiagnosticCode
from .diagnostic import (
    Diagnostic,
    DiagnosticCategory,
    DiagnosticSeverity,
    SourceLocation,
    SourceRange,
)
from .formatter import DiagnosticFormatter
from .reporter import DiagnosticReporter
from .suggestions import (
    BUILTIN_FUNCTIONS,
    KEYWORDS,
    find_best_match,
    suggest_builtin_function,
    suggest_keyword,
    suggest_variable,
)

__all__ = [
    "DiagnosticCode",
    "Diagnostic",
    "DiagnosticSeverity",
    "DiagnosticCategory",
    "SourceLocation",
    "SourceRange",
    "DiagnosticFormatter",
    "DiagnosticReporter",
    "find_best_match",
    "suggest_variable",
    "suggest_builtin_function",
    "suggest_keyword",
    "BUILTIN_FUNCTIONS",
    "KEYWORDS",
]
