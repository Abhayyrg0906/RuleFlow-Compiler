"""Parser exception definitions for RuleFlow Compiler."""

from typing import Optional
from ruleflow.lexer.lexer import Token
from ruleflow.diagnostics.codes import DiagnosticCode
from ruleflow.diagnostics.diagnostic import Diagnostic, DiagnosticCategory, DiagnosticSeverity


class ParserError(Exception):
    """Exception raised when syntax analysis fails."""

    def __init__(
        self,
        message: str,
        line: int,
        column: int,
        found_token: Optional[Token] = None,
        code: Optional[str] = None,
        suggestion: Optional[str] = None,
        source_line: Optional[str] = None,
    ):
        self.message = message
        self.line = line
        self.column = column
        self.found_token = found_token

        if code is None:
            if "expected" in message.lower():
                code = DiagnosticCode.SYN_MISSING_TOKEN
            elif "unexpected" in message.lower():
                code = DiagnosticCode.SYN_UNEXPECTED_TOKEN
            else:
                code = DiagnosticCode.SYN_INVALID_STATEMENT
        self.code = code
        self.suggestion = suggestion
        self.source_line = source_line

        self.diagnostic = Diagnostic(
            code=self.code,
            category=DiagnosticCategory.SYNTAX,
            severity=DiagnosticSeverity.ERROR,
            message=message,
            line=line,
            column=column,
            source_line=source_line,
            suggestion=suggestion,
        )
        super().__init__(f"[Line {line}, Col {column}] Syntax Error: {message}")
