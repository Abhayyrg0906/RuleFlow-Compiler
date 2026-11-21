"""Centralized DiagnosticReporter collecting and managing diagnostics."""

from typing import Any, Dict, List, Optional
from .diagnostic import Diagnostic, DiagnosticCategory, DiagnosticSeverity
from .formatter import DiagnosticFormatter


class DiagnosticReporter:
    """Collects, queries, and formats compiler diagnostics across pipeline stages."""

    def __init__(self, source_code: Optional[str] = None):
        self.source_code = source_code
        self._diagnostics: List[Diagnostic] = []

    def set_source_code(self, source_code: str) -> None:
        """Update the source code used for diagnostic snippets."""
        self.source_code = source_code

    def add(self, diagnostic: Diagnostic) -> None:
        """Add an already constructed Diagnostic instance."""
        # Auto-populate source line if missing and source_code is available
        if diagnostic.source_line is None and self.source_code and diagnostic.line:
            diagnostic.source_line = DiagnosticFormatter.extract_source_line(
                self.source_code, diagnostic.line
            )
        self._diagnostics.append(diagnostic)

    def error(
        self,
        code: str,
        message: str,
        category: DiagnosticCategory,
        line: Optional[int] = None,
        column: Optional[int] = None,
        end_line: Optional[int] = None,
        end_column: Optional[int] = None,
        source_line: Optional[str] = None,
        suggestion: Optional[str] = None,
        related_info: Optional[str] = None,
    ) -> Diagnostic:
        """Report an ERROR diagnostic."""
        diag = Diagnostic(
            code=code,
            category=category,
            severity=DiagnosticSeverity.ERROR,
            message=message,
            line=line,
            column=column,
            end_line=end_line,
            end_column=end_column,
            source_line=source_line,
            suggestion=suggestion,
            related_info=related_info,
        )
        self.add(diag)
        return diag

    def warning(
        self,
        code: str,
        message: str,
        category: DiagnosticCategory,
        line: Optional[int] = None,
        column: Optional[int] = None,
        suggestion: Optional[str] = None,
        related_info: Optional[str] = None,
    ) -> Diagnostic:
        """Report a WARNING diagnostic."""
        diag = Diagnostic(
            code=code,
            category=category,
            severity=DiagnosticSeverity.WARNING,
            message=message,
            line=line,
            column=column,
            suggestion=suggestion,
            related_info=related_info,
        )
        self.add(diag)
        return diag

    def info(
        self,
        code: str,
        message: str,
        category: DiagnosticCategory,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> Diagnostic:
        """Report an INFO diagnostic."""
        diag = Diagnostic(
            code=code,
            category=category,
            severity=DiagnosticSeverity.INFO,
            message=message,
            line=line,
            column=column,
        )
        self.add(diag)
        return diag

    def has_errors(self) -> bool:
        """Check if any ERROR severity diagnostics have been recorded."""
        return any(d.severity == DiagnosticSeverity.ERROR for d in self._diagnostics)

    def has_warnings(self) -> bool:
        """Check if any WARNING severity diagnostics have been recorded."""
        return any(d.severity == DiagnosticSeverity.WARNING for d in self._diagnostics)

    def get_diagnostics(self) -> List[Diagnostic]:
        """Return all recorded diagnostics."""
        return list(self._diagnostics)

    def get_errors(self) -> List[Diagnostic]:
        """Return only ERROR severity diagnostics."""
        return [d for d in self._diagnostics if d.severity == DiagnosticSeverity.ERROR]

    def get_warnings(self) -> List[Diagnostic]:
        """Return only WARNING severity diagnostics."""
        return [d for d in self._diagnostics if d.severity == DiagnosticSeverity.WARNING]

    def format_all(self) -> str:
        """Format all recorded diagnostics using DiagnosticFormatter."""
        return DiagnosticFormatter.format_all(self._diagnostics, source_code=self.source_code)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Return all diagnostics as a list of dictionaries for UI/serialization."""
        return [d.to_dict() for d in self._diagnostics]

    def clear(self) -> None:
        """Clear all stored diagnostics."""
        self._diagnostics.clear()

    def __len__(self) -> int:
        return len(self._diagnostics)

    def __iter__(self):
        return iter(self._diagnostics)
