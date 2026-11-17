"""Lexer module for RuleFlow Compiler.

Performs lexical analysis by converting raw source text into a stream of tokens,
tracking line and column positions, and reporting meaningful syntax errors.
"""

from typing import Any, Dict, List, Optional
from .token_types import TokenType
from .errors import LexerError


class Token:
    """Represents a single lexical token produced by the Lexer."""

    def __init__(self, token_type: TokenType, value: Any, line: int = 1, column: int = 1):
        self.type = token_type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self) -> str:
        type_str = self.type.value if hasattr(self.type, "value") else str(self.type)
        return f"Token({type_str}, {repr(self.value)}, line={self.line}, col={self.column})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Token):
            return (
                self.type == other.type
                and self.value == other.value
                and self.line == other.line
                and self.column == other.column
            )
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert token to a dictionary format suitable for UI display and serialization."""
        return {
            "type": self.type.value if hasattr(self.type, "value") else str(self.type),
            "value": self.value,
            "line": self.line,
            "column": self.column,
        }


class Lexer:
    """Tokenizer for the RuleFlow language."""

    KEYWORDS: Dict[str, TokenType] = {
        "RULE": TokenType.RULE,
        "IF": TokenType.IF,
        "THEN": TokenType.THEN,
        "ELSE": TokenType.ELSE,
        "END": TokenType.END,
        "AND": TokenType.AND,
        "OR": TokenType.OR,
        "NOT": TokenType.NOT,
        # Lowercase aliases for developer friendliness
        "rule": TokenType.RULE,
        "if": TokenType.IF,
        "then": TokenType.THEN,
        "else": TokenType.ELSE,
        "end": TokenType.END,
        "and": TokenType.AND,
        "or": TokenType.OR,
        "not": TokenType.NOT,
    }

    ESCAPE_CHARACTERS: Dict[str, str] = {
        "n": "\n",
        "t": "\t",
        "r": "\r",
        "\\": "\\",
        '"': '"',
        "'": "'",
    }

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.position = 0
        self.line = 1
        self.column = 1
        self.total_length = len(source_code)

    def current_char(self) -> Optional[str]:
        """Return the character at the current position or None if at EOF."""
        if self.position >= self.total_length:
            return None
        return self.source_code[self.position]

    def peek(self, offset: int = 1) -> Optional[str]:
        """Look ahead by `offset` characters without moving the cursor."""
        peek_pos = self.position + offset
        if peek_pos >= self.total_length:
            return None
        return self.source_code[peek_pos]

    def advance(self) -> Optional[str]:
        """Move cursor forward by 1 character and update line and column positions."""
        char = self.current_char()
        if char is not None:
            self.position += 1
            if char == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        return char

    def skip_whitespace(self) -> None:
        """Skip whitespace characters while maintaining accurate line and column counters."""
        while self.current_char() is not None and self.current_char() in " \t\r\n":
            self.advance()

    def skip_comment(self) -> None:
        """Skip single-line comments started by '//' or '#'."""
        while self.current_char() is not None and self.current_char() not in "\r\n":
            self.advance()

    def read_identifier_or_keyword(self) -> Token:
        """Read an identifier or reserved RuleFlow keyword."""
        start_line = self.line
        start_col = self.column
        chars: List[str] = []

        while self.current_char() is not None and (self.current_char().isalnum() or self.current_char() == "_"):
            chars.append(self.advance())  # type: ignore

        word = "".join(chars)
        token_type = self.KEYWORDS.get(word, TokenType.IDENTIFIER)
        return Token(token_type, word, start_line, start_col)

    def read_number(self) -> Token:
        """Read an integer or decimal number literal."""
        start_line = self.line
        start_col = self.column
        num_chars: List[str] = []
        is_decimal = False

        while self.current_char() is not None and self.current_char().isdigit():
            num_chars.append(self.advance())  # type: ignore

        # Check for fractional part
        if self.current_char() == ".":
            next_char = self.peek()
            if next_char is not None and next_char.isdigit():
                is_decimal = True
                num_chars.append(self.advance())  # type: ignore (consume '.')
                while self.current_char() is not None and self.current_char().isdigit():
                    num_chars.append(self.advance())  # type: ignore
            else:
                # A dot with no following digits is invalid syntax
                raise LexerError(
                    f"Invalid decimal literal '{''.join(num_chars)}.': Expected at least one digit after '.'",
                    self.line,
                    self.column,
                    char=".",
                )

        raw_str = "".join(num_chars)
        if is_decimal:
            return Token(TokenType.DECIMAL, float(raw_str), start_line, start_col)
        return Token(TokenType.INTEGER, int(raw_str), start_line, start_col)

    def read_string(self, quote_char: str) -> Token:
        """Read a string literal enclosed by double or single quotes."""
        start_line = self.line
        start_col = self.column
        self.advance()  # Skip opening quote

        chars: List[str] = []
        while True:
            char = self.current_char()
            if char is None or char in "\r\n":
                raise LexerError(
                    f"Unterminated string literal starting at line {start_line}, col {start_col}",
                    start_line,
                    start_col,
                    char=quote_char,
                )

            if char == "\\":
                # Handle escape sequence
                self.advance()
                escaped = self.current_char()
                if escaped is None:
                    raise LexerError(
                        f"Unterminated escape sequence in string literal",
                        self.line,
                        self.column,
                        char="\\",
                    )
                chars.append(self.ESCAPE_CHARACTERS.get(escaped, escaped))
                self.advance()
            elif char == quote_char:
                self.advance()  # Skip closing quote
                break
            else:
                chars.append(char)
                self.advance()

        return Token(TokenType.STRING, "".join(chars), start_line, start_col)

    def tokenize(self) -> List[Token]:
        """Convert the entire source code into a list of tokens.

        Raises:
            LexerError: If an unrecognized character or malformed literal is encountered.
        """
        tokens: List[Token] = []

        while self.current_char() is not None:
            char = self.current_char()

            # 1. Skip whitespace
            if char in " \t\r\n":
                self.skip_whitespace()
                continue

            # 2. Skip comments: // or #
            if char == "#":
                self.skip_comment()
                continue

            if char == "/" and self.peek() == "/":
                self.skip_comment()
                continue

            start_line = self.line
            start_col = self.column

            # 3. Identifiers and Keywords
            if char.isalpha() or char == "_":
                tokens.append(self.read_identifier_or_keyword())
                continue

            # 4. Numbers (Integers and Decimals)
            if char.isdigit():
                tokens.append(self.read_number())
                continue

            # 5. Strings ("..." or '...')
            if char in ('"', "'"):
                tokens.append(self.read_string(char))
                continue

            # 6. Relational Operators & Assignment
            if char == "=":
                if self.peek() == "=":
                    self.advance()
                    self.advance()
                    tokens.append(Token(TokenType.EQUALS, "==", start_line, start_col))
                else:
                    self.advance()
                    tokens.append(Token(TokenType.ASSIGN, "=", start_line, start_col))
                continue

            if char == "!":
                if self.peek() == "=":
                    self.advance()
                    self.advance()
                    tokens.append(Token(TokenType.NOT_EQUALS, "!=", start_line, start_col))
                else:
                    raise LexerError(
                        f"Unexpected character '!'. Did you mean '!='?",
                        start_line,
                        start_col,
                        char="!",
                    )
                continue

            if char == "<":
                if self.peek() == "=":
                    self.advance()
                    self.advance()
                    tokens.append(Token(TokenType.LESS_EQUAL, "<=", start_line, start_col))
                else:
                    self.advance()
                    tokens.append(Token(TokenType.LESS_THAN, "<", start_line, start_col))
                continue

            if char == ">":
                if self.peek() == "=":
                    self.advance()
                    self.advance()
                    tokens.append(Token(TokenType.GREATER_EQUAL, ">=", start_line, start_col))
                else:
                    self.advance()
                    tokens.append(Token(TokenType.GREATER_THAN, ">", start_line, start_col))
                continue

            # 7. Arithmetic Operators
            if char == "+":
                self.advance()
                tokens.append(Token(TokenType.PLUS, "+", start_line, start_col))
                continue

            if char == "-":
                self.advance()
                tokens.append(Token(TokenType.MINUS, "-", start_line, start_col))
                continue

            if char == "*":
                self.advance()
                tokens.append(Token(TokenType.MULTIPLY, "*", start_line, start_col))
                continue

            if char == "/":
                self.advance()
                tokens.append(Token(TokenType.DIVIDE, "/", start_line, start_col))
                continue

            if char == "%":
                self.advance()
                tokens.append(Token(TokenType.MODULO, "%", start_line, start_col))
                continue

            # 8. Parentheses & Delimiters
            if char == "(":
                self.advance()
                tokens.append(Token(TokenType.LPAREN, "(", start_line, start_col))
                continue

            if char == ")":
                self.advance()
                tokens.append(Token(TokenType.RPAREN, ")", start_line, start_col))
                continue

            if char == ":":
                self.advance()
                tokens.append(Token(TokenType.COLON, ":", start_line, start_col))
                continue

            if char == ",":
                self.advance()
                tokens.append(Token(TokenType.COMMA, ",", start_line, start_col))
                continue

            # 9. Invalid character encountered
            invalid_char = char
            self.advance()
            raise LexerError(
                f"Invalid character '{invalid_char}' encountered.",
                start_line,
                start_col,
                char=invalid_char,
            )

        # Append End-Of-File token
        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return tokens
