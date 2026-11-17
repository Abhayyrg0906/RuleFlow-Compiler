"""Comprehensive unit tests for RuleFlow Parser (Module 2)."""

from pathlib import Path
import pytest

from ruleflow.lexer import Lexer
from ruleflow.ast import (
    ProgramNode,
    RuleDeclarationNode,
    IfStatementNode,
    AssignmentNode,
    BinaryOpNode,
    UnaryOpNode,
    LiteralNode,
    IdentifierNode,
)
from ruleflow.parser import Parser, ParserError


def parse_code(code: str) -> ProgramNode:
    """Helper function to tokenize and parse a code string."""
    tokens = Lexer(code).tokenize()
    return Parser(tokens).parse()


# -------------------------------------------------------------
# 1. Valid Program & Grammar Tests
# -------------------------------------------------------------

def test_empty_program():
    """Verify that an empty input produces an empty ProgramNode."""
    ast = parse_code("")
    assert isinstance(ast, ProgramNode)
    assert len(ast.statements) == 0


def test_rule_declaration_with_colon():
    """Verify parsing a basic RULE declaration with a colon."""
    code = """
    RULE SimpleRule:
        x = 10
    """
    ast = parse_code(code)
    assert len(ast.statements) == 1
    rule = ast.statements[0]
    assert isinstance(rule, RuleDeclarationNode)
    assert rule.name == "SimpleRule"
    assert len(rule.body) == 1
    assert isinstance(rule.body[0], AssignmentNode)
    assert rule.body[0].target == "x"
    assert rule.body[0].value.value == 10


def test_rule_declaration_with_end():
    """Verify parsing a RULE declaration closed by an optional END keyword."""
    code = """
    RULE ExplicitEndRule
        total = 100.5
    END
    """
    ast = parse_code(code)
    assert len(ast.statements) == 1
    rule = ast.statements[0]
    assert isinstance(rule, RuleDeclarationNode)
    assert rule.name == "ExplicitEndRule"
    assert len(rule.body) == 1
    assert rule.body[0].target == "total"
    assert rule.body[0].value.value == 100.5


def test_multiple_assignments():
    """Verify multiple assignments in sequence."""
    code = """
    RULE SetupVariables:
        a = 1
        b = 2.5
        c = "Done"
    """
    ast = parse_code(code)
    rule = ast.statements[0]
    assert len(rule.body) == 3
    assert rule.body[0].target == "a"
    assert rule.body[0].value.value == 1
    assert rule.body[1].target == "b"
    assert rule.body[1].value.value == 2.5
    assert rule.body[2].target == "c"
    assert rule.body[2].value.value == "Done"


def test_arithmetic_precedence():
    """Verify operator precedence: * and / bind tighter than + and -."""
    code = """
    RULE MathRule:
        res = 2 + 3 * 4
    """
    ast = parse_code(code)
    assignment = ast.statements[0].body[0]
    expr = assignment.value

    # Expect: 2 + (3 * 4)
    assert isinstance(expr, BinaryOpNode)
    assert expr.op == "+"
    assert isinstance(expr.left, LiteralNode)
    assert expr.left.value == 2
    assert isinstance(expr.right, BinaryOpNode)
    assert expr.right.op == "*"
    assert expr.right.left.value == 3
    assert expr.right.right.value == 4


def test_parenthesized_expressions():
    """Verify that parentheses override default arithmetic precedence."""
    code = """
    RULE GroupedMath:
        res = (2 + 3) * 4
    """
    ast = parse_code(code)
    assignment = ast.statements[0].body[0]
    expr = assignment.value

    # Expect: (2 + 3) * 4
    assert isinstance(expr, BinaryOpNode)
    assert expr.op == "*"
    assert isinstance(expr.left, BinaryOpNode)
    assert expr.left.op == "+"
    assert expr.left.left.value == 2
    assert expr.left.right.value == 3
    assert expr.right.value == 4


def test_unary_operators():
    """Verify unary operators: negative numbers and NOT expressions."""
    code = """
    RULE UnaryRule:
        x = -15
        flag = NOT is_active
    """
    ast = parse_code(code)
    rule = ast.statements[0]

    # x = -15
    assign_x = rule.body[0]
    assert isinstance(assign_x.value, UnaryOpNode)
    assert assign_x.value.op == "-"
    assert assign_x.value.operand.value == 15

    # flag = NOT is_active
    assign_flag = rule.body[1]
    assert isinstance(assign_flag.value, UnaryOpNode)
    assert assign_flag.value.op == "NOT"
    assert isinstance(assign_flag.value.operand, IdentifierNode)
    assert assign_flag.value.operand.name == "is_active"


def test_logical_and_relational_precedence():
    """Verify that relational operators bind tighter than AND / OR."""
    code = """
    RULE CheckCondition:
        IF score > 50 AND age <= 25 OR status == "VIP" THEN
            eligible = 1
        END
    """
    ast = parse_code(code)
    if_stmt = ast.statements[0].body[0]
    assert isinstance(if_stmt, IfStatementNode)

    # Condition: ((score > 50) AND (age <= 25)) OR (status == "VIP")
    cond = if_stmt.condition
    assert isinstance(cond, BinaryOpNode)
    assert cond.op == "OR"
    assert cond.left.op == "AND"
    assert cond.left.left.op == ">"
    assert cond.left.right.op == "<="
    assert cond.right.op == "=="


def test_if_then_without_else():
    """Verify IF-THEN statement without an ELSE branch."""
    code = """
    RULE SimpleCondition:
        IF x == 10 THEN
            y = 20
        END
    """
    ast = parse_code(code)
    if_stmt = ast.statements[0].body[0]
    assert isinstance(if_stmt, IfStatementNode)
    assert len(if_stmt.then_branch) == 1
    assert len(if_stmt.else_branch) == 0
    assert if_stmt.then_branch[0].target == "y"


def test_if_then_else():
    """Verify IF-THEN-ELSE conditional statement."""
    code = """
    RULE BranchRule:
        IF total >= 100 THEN
            discount = 10
        ELSE
            discount = 0
        END
    """
    ast = parse_code(code)
    if_stmt = ast.statements[0].body[0]
    assert isinstance(if_stmt, IfStatementNode)
    assert len(if_stmt.then_branch) == 1
    assert len(if_stmt.else_branch) == 1
    assert if_stmt.then_branch[0].target == "discount"
    assert if_stmt.then_branch[0].value.value == 10
    assert if_stmt.else_branch[0].target == "discount"
    assert if_stmt.else_branch[0].value.value == 0


def test_nested_if_statements():
    """Verify nested IF statements."""
    code = """
    RULE NestedRule:
        IF a == 1 THEN
            IF b == 2 THEN
                c = 3
            END
        END
    """
    ast = parse_code(code)
    outer_if = ast.statements[0].body[0]
    assert isinstance(outer_if, IfStatementNode)
    inner_if = outer_if.then_branch[0]
    assert isinstance(inner_if, IfStatementNode)
    assert inner_if.then_branch[0].target == "c"


# -------------------------------------------------------------
# 2. Student Eligibility Capstone Test (Requirement 9)
# -------------------------------------------------------------

def test_student_eligibility_example_ast():
    """Requirement 9: Test using examples/student_eligibility.rf."""
    file_path = Path(__file__).parent.parent / "examples" / "student_eligibility.rf"
    code = file_path.read_text(encoding="utf-8")

    ast = parse_code(code)

    assert isinstance(ast, ProgramNode)
    assert len(ast.statements) == 1

    rule = ast.statements[0]
    assert isinstance(rule, RuleDeclarationNode)
    assert rule.name == "StudentEligibility"
    assert len(rule.body) == 1

    if_stmt = rule.body[0]
    assert isinstance(if_stmt, IfStatementNode)

    # Condition: gpa >= 3.5 AND attendance >= 75
    cond = if_stmt.condition
    assert isinstance(cond, BinaryOpNode)
    assert cond.op == "AND"

    # Left: gpa >= 3.5
    left_cond = cond.left
    assert isinstance(left_cond, BinaryOpNode)
    assert left_cond.op == ">="
    assert isinstance(left_cond.left, IdentifierNode)
    assert left_cond.left.name == "gpa"
    assert isinstance(left_cond.right, LiteralNode)
    assert left_cond.right.value == 3.5
    assert left_cond.right.literal_type == "DECIMAL"

    # Right: attendance >= 75
    right_cond = cond.right
    assert isinstance(right_cond, BinaryOpNode)
    assert right_cond.op == ">="
    assert isinstance(right_cond.left, IdentifierNode)
    assert right_cond.left.name == "attendance"
    assert isinstance(right_cond.right, LiteralNode)
    assert right_cond.right.value == 75
    assert right_cond.right.literal_type == "INTEGER"

    # Then Branch: status = "Eligible"
    assert len(if_stmt.then_branch) == 1
    then_assign = if_stmt.then_branch[0]
    assert isinstance(then_assign, AssignmentNode)
    assert then_assign.target == "status"
    assert isinstance(then_assign.value, LiteralNode)
    assert then_assign.value.value == "Eligible"
    assert then_assign.value.literal_type == "STRING"

    # Else Branch: status = "Not Eligible"
    assert len(if_stmt.else_branch) == 1
    else_assign = if_stmt.else_branch[0]
    assert isinstance(else_assign, AssignmentNode)
    assert else_assign.target == "status"
    assert isinstance(else_assign.value, LiteralNode)
    assert else_assign.value.value == "Not Eligible"
    assert else_assign.value.literal_type == "STRING"


# -------------------------------------------------------------
# 3. Syntax Error Detection & Reporting Tests
# -------------------------------------------------------------

def test_missing_rule_identifier():
    """Verify error when RULE keyword is not followed by an identifier."""
    code = "RULE : x = 10"
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)

    err = exc_info.value
    assert err.line == 1
    assert err.column == 6
    assert "Expected rule name identifier after 'RULE'" in err.message


def test_missing_then_keyword():
    """Verify error when IF condition is not followed by THEN."""
    code = """
    RULE TestRule:
        IF x > 5
            y = 10
        END
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)

    err = exc_info.value
    assert "Expected 'THEN' after IF condition" in err.message


def test_missing_end_keyword():
    """Verify error when IF statement is missing closing END."""
    code = """
    RULE TestRule:
        IF x > 5 THEN
            y = 10
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)

    err = exc_info.value
    assert "Expected 'END' to close IF statement" in err.message


def test_unmatched_parenthesis():
    """Verify error when an open parenthesis is not closed."""
    code = """
    RULE MathRule:
        x = (2 + 3 * 4
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)

    err = exc_info.value
    assert "Expected ')' to close opening '('" in err.message


def test_unexpected_token_in_expression():
    """Verify error when expression contains an unexpected token."""
    code = """
    RULE BadExpr:
        x = 5 + * 3
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)

    err = exc_info.value
    assert "Unexpected token in expression" in err.message


def test_invalid_statement_start():
    """Verify error when a statement begins with an invalid token."""
    code = """
    RULE BadStmt:
        == 5
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)

    err = exc_info.value
    assert "Unexpected token '==' at start of statement" in err.message
