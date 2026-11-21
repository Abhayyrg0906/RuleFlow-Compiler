"""Lexer exception definitions for RuleFlow Compiler."""

from typing import Optional
from ruleflow.diagnostics.codes import DiagnosticCode
from ruleflow.diagnostics.diagnostic import Diagnostic, DiagnosticCategory, DiagnosticSeverity


class LexerError(Exception):
    """Exception raised when lexical analysis encounters an invalid character or token sequence."""

    def __init__(
        self,
        message: str,
        line: int,
        column: int,
        char: Optional[str] = None,
        code: Optional[str] = None,
        suggestion: Optional[str] = None,
        source_line: Optional[str] = None,
    ):
        self.message = message
        self.line = line
        self.column = column
        self.char = char

        if code is None:
            if "unterminated string" in message.lower():
                code = DiagnosticCode.LEX_UNTERMINATED_STRING
            else:
                code = DiagnosticCode.LEX_INVALID_CHAR
        self.code = code
        self.suggestion = suggestion
        self.source_line = source_line

        self.diagnostic = Diagnostic(
            code=self.code,
            category=DiagnosticCategory.LEXICAL,
            severity=DiagnosticSeverity.ERROR,
            message=message,
            line=line,
            column=column,
            source_line=source_line,
            suggestion=suggestion,
        )
        super().__init__(f"[Line {line}, Col {column}] {message}")
