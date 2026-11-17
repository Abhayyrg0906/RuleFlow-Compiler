"""Parser exception definitions for RuleFlow Compiler."""

from typing import Optional
from ruleflow.lexer.lexer import Token


class ParserError(Exception):
    """Exception raised when syntax analysis fails."""

    def __init__(self, message: str, line: int, column: int, found_token: Optional[Token] = None):
        self.message = message
        self.line = line
        self.column = column
        self.found_token = found_token
        super().__init__(f"[Line {line}, Col {column}] Syntax Error: {message}")
