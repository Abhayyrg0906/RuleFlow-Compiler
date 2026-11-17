"""Token type definitions for the RuleFlow Lexer."""

from enum import Enum


class TokenType(str, Enum):
    """Enumeration of all supported token types in RuleFlow."""

    # Keywords
    RULE = "RULE"
    IF = "IF"
    THEN = "THEN"
    ELSE = "ELSE"
    END = "END"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

    # Identifiers & Literals
    IDENTIFIER = "IDENTIFIER"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    STRING = "STRING"

    # Arithmetic Operators
    PLUS = "PLUS"          # +
    MINUS = "MINUS"        # -
    MULTIPLY = "MULTIPLY"  # *
    DIVIDE = "DIVIDE"      # /
    MODULO = "MODULO"      # %

    # Relational Operators
    EQUALS = "EQUALS"              # ==
    NOT_EQUALS = "NOT_EQUALS"      # !=
    LESS_THAN = "LESS_THAN"        # <
    GREATER_THAN = "GREATER_THAN"  # >
    LESS_EQUAL = "LESS_EQUAL"      # <=
    GREATER_EQUAL = "GREATER_EQUAL"# >=

    # Assignment Operator
    ASSIGN = "ASSIGN"      # =

    # Parentheses & Delimiters
    LPAREN = "LPAREN"      # (
    RPAREN = "RPAREN"      # )
    COLON = "COLON"        # :
    COMMA = "COMMA"        # ,

    # End of File
    EOF = "EOF"

    def __str__(self) -> str:
        return self.value
