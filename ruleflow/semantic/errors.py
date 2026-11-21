"""Semantic error exception definitions for RuleFlow Compiler."""

from typing import Optional
from ruleflow.diagnostics.codes import DiagnosticCode
from ruleflow.diagnostics.diagnostic import Diagnostic, DiagnosticCategory, DiagnosticSeverity


class SemanticError(Exception):
    """Exception raised when semantic validation, scope resolution, or type checking fails."""

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        identifier: Optional[str] = None,
        operator: Optional[str] = None,
        code: Optional[str] = None,
        suggestion: Optional[str] = None,
        source_line: Optional[str] = None,
        related_info: Optional[str] = None,
    ):
        self.message = message
        self.line = line
        self.column = column
        self.identifier = identifier
        self.operator = operator
        self.suggestion = suggestion
        self.source_line = source_line
        self.related_info = related_info

        # Infer diagnostic code if not provided
        if code is None:
            low = message.lower()
            if "undefined variable" in low:
                code = DiagnosticCode.SEM_UNDEFINED_VARIABLE
            elif "duplicate" in low:
                code = DiagnosticCode.SEM_DUPLICATE_DECLARATION
            elif "recursive" in low or "circular" in low:
                code = DiagnosticCode.SEM_RECURSION_OR_CIRCULAR
            elif "return" in low and ("missing" in low or "outside" in low or "multiple" in low):
                code = DiagnosticCode.SEM_INVALID_RETURN
            elif "function" in low and ("expects" in low or "argument" in low or "unknown function" in low):
                code = DiagnosticCode.SEM_INVALID_FUNCTION_CALL
            elif "division by literal zero" in low or "modulo by literal zero" in low:
                code = DiagnosticCode.SEM_ZERO_DIVISION_LITERAL
            elif "assigned in only" in low or "definite assignment" in low:
                code = DiagnosticCode.SEM_INDEFINITE_ASSIGNMENT
            else:
                code = DiagnosticCode.SEM_TYPE_MISMATCH
        self.code = code

        self.diagnostic = Diagnostic(
            code=self.code,
            category=DiagnosticCategory.SEMANTIC,
            severity=DiagnosticSeverity.ERROR,
            message=message,
            line=line,
            column=column,
            source_line=source_line,
            suggestion=suggestion,
            related_info=related_info,
        )

        location = ""
        if line is not None and column is not None:
            location = f"[Line {line}, Col {column}] "
        elif line is not None:
            location = f"[Line {line}] "

        super().__init__(f"{location}Semantic Error: {message}")
