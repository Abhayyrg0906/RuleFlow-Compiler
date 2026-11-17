"""Lexer exception definitions for RuleFlow Compiler."""

from typing import Optional


class LexerError(Exception):
    """Exception raised when lexical analysis encounters an invalid character or token sequence."""

    def __init__(self, message: str, line: int, column: int, char: Optional[str] = None):
        self.message = message
        self.line = line
        self.column = column
        self.char = char
        super().__init__(f"[Line {line}, Col {column}] {message}")
