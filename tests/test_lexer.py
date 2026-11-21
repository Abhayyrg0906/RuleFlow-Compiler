"""Comprehensive unit tests for RuleFlow Lexer (Module 1)."""

import pytest
from ruleflow.lexer import Lexer, Token, TokenType, LexerError


def test_keywords():
    """Verify recognition of all RuleFlow keywords."""
    code = "RULE IF THEN ELSE END AND OR NOT"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    expected_types = [
        TokenType.RULE,
        TokenType.IF,
        TokenType.THEN,
        TokenType.ELSE,
        TokenType.END,
        TokenType.AND,
        TokenType.OR,
        TokenType.NOT,
        TokenType.EOF,
    ]
    assert [t.type for t in tokens] == expected_types
    assert [t.value for t in tokens[:-1]] == ["RULE", "IF", "THEN", "ELSE", "END", "AND", "OR", "NOT"]


def test_identifiers():
    """Verify recognition of valid identifiers."""
    code = "student_name gpaScore count_1 _private"
    tokens = Lexer(code).tokenize()

    assert [t.type for t in tokens[:-1]] == [TokenType.IDENTIFIER] * 4
    assert [t.value for t in tokens[:-1]] == ["student_name", "gpaScore", "count_1", "_private"]


def test_integers_and_decimals():
    """Verify recognition of integer and decimal literals."""
    code = "42 0 100 3.14 0.05 99.9"
    tokens = Lexer(code).tokenize()

    assert tokens[0].type == TokenType.INTEGER
    assert tokens[0].value == 42
    assert tokens[1].type == TokenType.INTEGER
    assert tokens[1].value == 0
    assert tokens[2].type == TokenType.INTEGER
    assert tokens[2].value == 100

    assert tokens[3].type == TokenType.DECIMAL
    assert tokens[3].value == 3.14
    assert tokens[4].type == TokenType.DECIMAL
    assert tokens[4].value == 0.05
    assert tokens[5].type == TokenType.DECIMAL
    assert tokens[5].value == 99.9


def test_strings():
    """Verify double-quoted and single-quoted strings with escape sequences."""
    code = '"Hello, World!" \'Single quoted\' "Line1\\nLine2" "Quote: \\"Hi\\""'
    tokens = Lexer(code).tokenize()

    assert [t.type for t in tokens[:-1]] == [TokenType.STRING] * 4
    assert tokens[0].value == "Hello, World!"
    assert tokens[1].value == "Single quoted"
    assert tokens[2].value == "Line1\nLine2"
    assert tokens[3].value == 'Quote: "Hi"'


def test_arithmetic_operators():
    """Verify recognition of arithmetic operators (+, -, *, /, %)."""
    code = "+ - * / %"
    tokens = Lexer(code).tokenize()

    expected = [
        TokenType.PLUS,
        TokenType.MINUS,
        TokenType.MULTIPLY,
        TokenType.DIVIDE,
        TokenType.MODULO,
        TokenType.EOF,
    ]
    assert [t.type for t in tokens] == expected


def test_relational_and_assignment_operators():
    """Verify recognition of relational (==, !=, <=, >=, <, >) and assignment (=) operators."""
    code = "= == != < <= > >="
    tokens = Lexer(code).tokenize()

    expected = [
        TokenType.ASSIGN,
        TokenType.EQUALS,
        TokenType.NOT_EQUALS,
        TokenType.LESS_THAN,
        TokenType.LESS_EQUAL,
        TokenType.GREATER_THAN,
        TokenType.GREATER_EQUAL,
        TokenType.EOF,
    ]
    assert [t.type for t in tokens] == expected


def test_parentheses_and_delimiters():
    """Verify parentheses and delimiters (parentheses, colon, comma)."""
    code = "( ) : ,"
    tokens = Lexer(code).tokenize()

    expected = [
        TokenType.LPAREN,
        TokenType.RPAREN,
        TokenType.COLON,
        TokenType.COMMA,
        TokenType.EOF,
    ]
    assert [t.type for t in tokens] == expected


def test_comments_and_whitespace():
    """Verify single-line comments (// and #) and whitespace are skipped correctly."""
    code = """
    // Leading comment
    RULE MyRule: # inline comment
        # Another full line comment
        x = 10 // trailing comment
    """
    tokens = Lexer(code).tokenize()

    # Should only contain: RULE, MyRule, :, x, =, 10, EOF
    expected = [
        (TokenType.RULE, "RULE"),
        (TokenType.IDENTIFIER, "MyRule"),
        (TokenType.COLON, ":"),
        (TokenType.IDENTIFIER, "x"),
        (TokenType.ASSIGN, "="),
        (TokenType.INTEGER, 10),
        (TokenType.EOF, ""),
    ]
    assert [(t.type, t.value) for t in tokens] == expected


def test_line_and_column_tracking():
    """Verify line and column numbers are accurately tracked."""
    code = "RULE\n   gpa\n     >="
    tokens = Lexer(code).tokenize()

    # Line 1: RULE at col 1
    assert tokens[0].type == TokenType.RULE
    assert tokens[0].line == 1
    assert tokens[0].column == 1

    # Line 2: gpa at col 4
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].line == 2
    assert tokens[1].column == 4

    # Line 3: >= at col 6
    assert tokens[2].type == TokenType.GREATER_EQUAL
    assert tokens[2].line == 3
    assert tokens[2].column == 6


def test_student_eligibility_example():
    """Requirement 8: Test using a student eligibility example containing IF, ELSE, AND, and relational operators."""
    code = """
    RULE StudentEligibility:
        IF gpa >= 3.5 AND attendance >= 75 THEN
            status = "Eligible"
        ELSE
            status = "Not Eligible"
        END
    """
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    # Filter out EOF for easier sequence verification
    token_pairs = [(t.type, t.value) for t in tokens if t.type != TokenType.EOF]

    expected_pairs = [
        (TokenType.RULE, "RULE"),
        (TokenType.IDENTIFIER, "StudentEligibility"),
        (TokenType.COLON, ":"),
        (TokenType.IF, "IF"),
        (TokenType.IDENTIFIER, "gpa"),
        (TokenType.GREATER_EQUAL, ">="),
        (TokenType.DECIMAL, 3.5),
        (TokenType.AND, "AND"),
        (TokenType.IDENTIFIER, "attendance"),
        (TokenType.GREATER_EQUAL, ">="),
        (TokenType.INTEGER, 75),
        (TokenType.THEN, "THEN"),
        (TokenType.IDENTIFIER, "status"),
        (TokenType.ASSIGN, "="),
        (TokenType.STRING, "Eligible"),
        (TokenType.ELSE, "ELSE"),
        (TokenType.IDENTIFIER, "status"),
        (TokenType.ASSIGN, "="),
        (TokenType.STRING, "Not Eligible"),
        (TokenType.END, "END"),
    ]

    assert token_pairs == expected_pairs


# --- Error Handling Tests ---

def test_invalid_character_error():
    """Verify that unexpected characters raise a descriptive LexerError."""
    code = "score = 95 @ 2"
    with pytest.raises(LexerError) as exc_info:
        Lexer(code).tokenize()

    error = exc_info.value
    assert error.line == 1
    assert error.column == 12
    assert error.char == "@"
    assert "Invalid character '@'" in error.message


def test_unexpected_exclamation_mark():
    """Verify that a standalone '!' raises a meaningful error hinting at '!='."""
    code = "IF x ! 5"
    with pytest.raises(LexerError) as exc_info:
        Lexer(code).tokenize()

    error = exc_info.value
    assert error.line == 1
    assert error.column == 6
    assert "Did you mean '!='?" in error.message


def test_invalid_decimal_literal():
    """Verify that a dot without fractional digits raises a LexerError."""
    code = "gpa = 3."
    with pytest.raises(LexerError) as exc_info:
        Lexer(code).tokenize()

    error = exc_info.value
    assert "Invalid decimal literal" in error.message


def test_unterminated_string_error():
    """Verify that an unterminated string raises a descriptive LexerError."""
    code = 'status = "Eligible'
    with pytest.raises(LexerError) as exc_info:
        Lexer(code).tokenize()

    error = exc_info.value
    assert "Unterminated string literal" in error.message


def test_while_and_do_keywords():
    """Verify recognition of WHILE and DO keywords and compatibility with similar identifiers."""
    code = "WHILE count > 0 DO while do while_count domain my_while dowhile"
    tokens = Lexer(code).tokenize()

    assert tokens[0].type == TokenType.WHILE
    assert tokens[0].value == "WHILE"
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[2].type == TokenType.GREATER_THAN
    assert tokens[3].type == TokenType.INTEGER
    assert tokens[4].type == TokenType.DO
    assert tokens[4].value == "DO"

    # Lowercase aliases
    assert tokens[5].type == TokenType.WHILE
    assert tokens[6].type == TokenType.DO

    # Identifiers containing while or do
    assert tokens[7].type == TokenType.IDENTIFIER
    assert tokens[7].value == "while_count"
    assert tokens[8].type == TokenType.IDENTIFIER
    assert tokens[8].value == "domain"
    assert tokens[9].type == TokenType.IDENTIFIER
    assert tokens[9].value == "my_while"
    assert tokens[10].type == TokenType.IDENTIFIER
    assert tokens[10].value == "dowhile"


def test_function_and_return_keywords():
    """Verify recognition of FUNCTION, RETURNS, and RETURN keywords and compatibility with similar identifiers."""
    code = "FUNCTION Calc RETURNS INTEGER RETURN result function returns return function_name returns_total return_val"
    tokens = Lexer(code).tokenize()

    assert tokens[0].type == TokenType.FUNCTION
    assert tokens[0].value == "FUNCTION"
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].value == "Calc"
    assert tokens[2].type == TokenType.RETURNS
    assert tokens[2].value == "RETURNS"
    assert tokens[3].type == TokenType.IDENTIFIER
    assert tokens[3].value == "INTEGER"
    assert tokens[4].type == TokenType.RETURN
    assert tokens[4].value == "RETURN"
    assert tokens[5].type == TokenType.IDENTIFIER
    assert tokens[5].value == "result"

    # Lowercase aliases
    assert tokens[6].type == TokenType.FUNCTION
    assert tokens[7].type == TokenType.RETURNS
    assert tokens[8].type == TokenType.RETURN

    # Identifiers containing function, returns, return
    assert tokens[9].type == TokenType.IDENTIFIER
    assert tokens[9].value == "function_name"
    assert tokens[10].type == TokenType.IDENTIFIER
    assert tokens[10].value == "returns_total"
    assert tokens[11].type == TokenType.IDENTIFIER
    assert tokens[11].value == "return_val"


