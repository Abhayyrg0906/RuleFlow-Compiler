"""Runtime execution exception definitions for RuleFlow Compiler."""

from typing import Any, Optional
from ruleflow.diagnostics.codes import DiagnosticCode
from ruleflow.diagnostics.diagnostic import Diagnostic, DiagnosticCategory, DiagnosticSeverity


class ExecutionError(Exception):
    """Exception raised when runtime evaluation of RuleFlow instructions fails."""

    def __init__(
        self,
        message: str,
        instruction: Optional[Any] = None,
        step: Optional[int] = None,
        code: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        suggestion: Optional[str] = None,
        source_line: Optional[str] = None,
    ):
        self.message = message
        self.instruction = instruction
        self.step = step
        self.line = line
        self.column = column
        self.suggestion = suggestion
        self.source_line = source_line

        if code is None:
            low = message.lower()
            if "division by zero" in low or "modulo by zero" in low:
                code = DiagnosticCode.RUN_DIVISION_BY_ZERO
            elif "step limit" in low:
                code = DiagnosticCode.RUN_STEP_LIMIT_EXCEEDED
            elif "undefined" in low or "not defined" in low:
                code = DiagnosticCode.RUN_UNDEFINED_VARIABLE
            else:
                code = DiagnosticCode.RUN_TYPE_ERROR
        self.code = code

        related_info = None
        if instruction is not None:
            related_info = f"Failed at instruction: {instruction}"

        self.diagnostic = Diagnostic(
            code=self.code,
            category=DiagnosticCategory.RUNTIME,
            severity=DiagnosticSeverity.ERROR,
            message=message,
            line=line,
            column=column,
            source_line=source_line,
            suggestion=suggestion,
            related_info=related_info,
        )

        loc = f"[Step {step}] " if step is not None else ""
        super().__init__(f"{loc}Execution Error: {message}")
