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


def test_nested_logical_and_arithmetic_expressions():
    """Verify complex nested logical and arithmetic expressions with parentheses."""
    code = """
    RULE ComplexRule:
        IF (score + bonus >= 100) AND NOT (is_penalized == 1) THEN
            tier = "Gold"
        END
    """
    ast = parse_code(code)
    if_stmt = ast.statements[0].body[0]
    cond = if_stmt.condition

    assert isinstance(cond, BinaryOpNode)
    assert cond.op == "AND"

    # Left: (score + bonus >= 100)
    left_rel = cond.left
    assert isinstance(left_rel, BinaryOpNode)
    assert left_rel.op == ">="
    assert left_rel.left.op == "+"
    assert left_rel.right.value == 100

    # Right: NOT (is_penalized == 1)
    right_not = cond.right
    assert isinstance(right_not, UnaryOpNode)
    assert right_not.op == "NOT"
    assert right_not.operand.op == "=="


def test_missing_assignment_value():
    """Verify error when an assignment statement is missing a value after '='."""
    code = """
    RULE BadAssign:
        x =
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)

    err = exc_info.value
    assert "Missing assignment value after '=' for variable 'x'" in err.message


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


# -------------------------------------------------------------
# 4. ELSE IF Branch Tests
# -------------------------------------------------------------

def test_single_else_if_branch():
    """Verify parsing a single ELSE IF branch."""
    code = """
    RULE SingleElseIf:
        IF x > 10 THEN
            y = 1
        ELSE IF x > 5 THEN
            y = 2
        ELSE
            y = 3
        END
    END
    """
    ast = parse_code(code)
    rule = ast.statements[0]
    if_stmt = rule.body[0]
    assert isinstance(if_stmt, IfStatementNode)
    assert len(if_stmt.then_branch) == 1
    assert len(if_stmt.elif_branches) == 1
    assert if_stmt.elif_branches[0].condition.op == ">"
    assert if_stmt.elif_branches[0].body[0].target == "y"
    assert len(if_stmt.else_branch) == 1


def test_multiple_else_if_branches_with_else():
    """Verify parsing multiple ELSE IF branches with final ELSE."""
    code = """
    RULE MultiElseIf:
        IF marks >= 90 THEN
            grade = "A"
        ELSE IF marks >= 75 THEN
            grade = "B"
        ELSE IF marks >= 60 THEN
            grade = "C"
        ELSE
            grade = "F"
        END
    END
    """
    ast = parse_code(code)
    rule = ast.statements[0]
    if_stmt = rule.body[0]
    assert isinstance(if_stmt, IfStatementNode)
    assert len(if_stmt.elif_branches) == 2
    assert if_stmt.elif_branches[0].condition.right.value == 75
    assert if_stmt.elif_branches[1].condition.right.value == 60
    assert len(if_stmt.else_branch) == 1
    assert if_stmt.else_branch[0].value.value == "F"


def test_else_if_without_else():
    """Verify parsing ELSE IF branches without a final ELSE."""
    code = """
    RULE ElseIfNoElse:
        IF score >= 90 THEN
            status = "Honors"
        ELSE IF score >= 70 THEN
            status = "Pass"
        END
    END
    """
    ast = parse_code(code)
    rule = ast.statements[0]
    if_stmt = rule.body[0]
    assert isinstance(if_stmt, IfStatementNode)
    assert len(if_stmt.elif_branches) == 1
    assert len(if_stmt.else_branch) == 0


def test_else_if_missing_condition_error():
    """Verify syntax error when ELSE IF is missing condition."""
    code = """
    RULE BadElseIf:
        IF x > 10 THEN
            y = 1
        ELSE IF THEN
            y = 2
        END
    END
    """
    with pytest.raises(ParserError):
        parse_code(code)


def test_else_if_missing_then_error():
    """Verify syntax error when ELSE IF is missing THEN keyword."""
    code = """
    RULE BadElseIfThen:
        IF x > 10 THEN
            y = 1
        ELSE IF x > 5
            y = 2
        END
    END
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)
    assert "Expected 'THEN' after ELSE IF condition" in exc_info.value.message


def test_else_if_after_else_error():
    """Verify syntax error when ELSE IF appears after an ELSE block."""
    code = """
    RULE InvalidOrder:
        IF x > 10 THEN
            y = 1
        ELSE
            y = 3
        ELSE IF x > 5 THEN
            y = 2
        END
    END
    """
    with pytest.raises(ParserError):
        parse_code(code)


# -------------------------------------------------------------
# 5. Built-in Function Call Parser Tests (Phase 7.2)
# -------------------------------------------------------------

def test_parse_builtin_function_calls():
    """Verify parsing of built-in function calls."""
    from ruleflow.ast.nodes import FunctionCallNode

    code = """
    RULE FunctionTest:
        a = ABS(-10)
        b = MIN(10, 20)
        c = MAX(10, 20)
        d = ROUND(12.6)
        e = LENGTH("RuleFlow")
    END
    """
    ast = parse_code(code)
    body = ast.statements[0].body
    assert len(body) == 5

    # a = ABS(-10)
    assert isinstance(body[0].value, FunctionCallNode)
    assert body[0].value.name == "ABS"
    assert len(body[0].value.args) == 1

    # b = MIN(10, 20)
    assert isinstance(body[1].value, FunctionCallNode)
    assert body[1].value.name == "MIN"
    assert len(body[1].value.args) == 2

    # c = MAX(10, 20)
    assert isinstance(body[2].value, FunctionCallNode)
    assert body[2].value.name == "MAX"
    assert len(body[2].value.args) == 2

    # d = ROUND(12.6)
    assert isinstance(body[3].value, FunctionCallNode)
    assert body[3].value.name == "ROUND"
    assert len(body[3].value.args) == 1

    # e = LENGTH("RuleFlow")
    assert isinstance(body[4].value, FunctionCallNode)
    assert body[4].value.name == "LENGTH"
    assert len(body[4].value.args) == 1


def test_parse_nested_function_calls():
    """Verify parsing of nested function calls and complex arguments."""
    from ruleflow.ast.nodes import FunctionCallNode, BinaryOpNode

    code = """
    RULE NestedFunctions:
        res = ABS(MIN(MAX(1, 2), -5)) + ROUND(10.5 * 2.0)
    END
    """
    ast = parse_code(code)
    stmt = ast.statements[0].body[0]
    assert isinstance(stmt.value, BinaryOpNode)
    assert stmt.value.op == "+"
    assert isinstance(stmt.value.left, FunctionCallNode)
    assert stmt.value.left.name == "ABS"
    assert isinstance(stmt.value.left.args[0], FunctionCallNode)
    assert stmt.value.left.args[0].name == "MIN"


def test_function_call_node_methods():
    """Verify FunctionCallNode to_dict, pretty, and repr methods."""
    from ruleflow.ast.nodes import FunctionCallNode, LiteralNode

    fn_node = FunctionCallNode(
        name="ABS",
        args=[LiteralNode(value=-5, literal_type="INTEGER", line=1, column=5)],
        line=1,
        column=1,
    )
    d = fn_node.to_dict()
    assert d["node_type"] == "FunctionCallNode"
    assert d["name"] == "ABS"
    assert len(d["args"]) == 1
    assert "FunctionCallNode: 'ABS'" in fn_node.pretty()
    assert repr(fn_node).startswith("FunctionCallNode(name='ABS'")


# -------------------------------------------------------------
# 6. WHILE Loop Parser Tests (Phase 7.3)
# -------------------------------------------------------------

def test_parse_basic_while_loop():
    """Verify parsing a basic WHILE loop."""
    from ruleflow.ast.nodes import WhileStatementNode, BinaryOpNode, AssignmentNode

    code = """
    RULE WhileDemo:
        WHILE count > 0 DO
            count = count - 1
        END
    END
    """
    ast = parse_code(code)
    rule = ast.statements[0]
    assert len(rule.body) == 1
    while_node = rule.body[0]
    assert isinstance(while_node, WhileStatementNode)
    assert isinstance(while_node.condition, BinaryOpNode)
    assert while_node.condition.op == ">"
    assert len(while_node.body) == 1
    assert isinstance(while_node.body[0], AssignmentNode)


def test_parse_empty_while_loop_body():
    """Verify parsing a WHILE loop with an empty body."""
    from ruleflow.ast.nodes import WhileStatementNode

    code = """
    RULE EmptyWhile:
        WHILE active DO
        END
    END
    """
    ast = parse_code(code)
    while_node = ast.statements[0].body[0]
    assert isinstance(while_node, WhileStatementNode)
    assert len(while_node.body) == 0


def test_parse_while_missing_do_error():
    """Verify syntax error when DO keyword is missing."""
    code = """
    RULE MissingDo:
        WHILE count > 0
            count = count - 1
        END
    END
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)
    assert "Expected 'DO' after WHILE condition" in exc_info.value.message


def test_parse_while_missing_end_error():
    """Verify syntax error when END keyword is missing."""
    code = """
    RULE MissingEnd:
        WHILE count > 0 DO
            count = count - 1
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)
    assert "Expected 'END' to close WHILE loop" in exc_info.value.message


def test_parse_nested_while_loops():
    """Verify parsing of nested WHILE loops."""
    from ruleflow.ast.nodes import WhileStatementNode

    code = """
    RULE NestedLoops:
        i = 0
        WHILE i < 3 DO
            j = 0
            WHILE j < 3 DO
                j = j + 1
            END
            i = i + 1
        END
    END
    """
    ast = parse_code(code)
    body = ast.statements[0].body
    outer_while = body[1]
    assert isinstance(outer_while, WhileStatementNode)
    assert len(outer_while.body) == 3
    inner_while = outer_while.body[1]
    assert isinstance(inner_while, WhileStatementNode)
    assert len(inner_while.body) == 1


def test_parse_if_inside_while():
    """Verify parsing of IF/ELSE statements nested inside a WHILE loop."""
    from ruleflow.ast.nodes import WhileStatementNode, IfStatementNode

    code = """
    RULE IfInWhile:
        WHILE count > 0 DO
            IF count % 2 == 0 THEN
                evens = evens + 1
            ELSE
                odds = odds + 1
            END
            count = count - 1
        END
    END
    """
    ast = parse_code(code)
    while_node = ast.statements[0].body[0]
    assert isinstance(while_node, WhileStatementNode)
    assert len(while_node.body) == 2
    assert isinstance(while_node.body[0], IfStatementNode)


def test_parse_while_inside_if():
    """Verify parsing of a WHILE loop nested inside an IF statement."""
    from ruleflow.ast.nodes import WhileStatementNode, IfStatementNode

    code = """
    RULE WhileInIf:
        IF flag THEN
            WHILE count > 0 DO
                count = count - 1
            END
        END
    END
    """
    ast = parse_code(code)
    if_node = ast.statements[0].body[0]
    assert isinstance(if_node, IfStatementNode)
    assert len(if_node.then_branch) == 1
    assert isinstance(if_node.then_branch[0], WhileStatementNode)


def test_parse_multiple_sequential_while_loops():
    """Verify parsing of sequential WHILE loops within the same rule."""
    from ruleflow.ast.nodes import WhileStatementNode

    code = """
    RULE SequentialWhiles:
        WHILE a > 0 DO
            a = a - 1
        END
        WHILE b > 0 DO
            b = b - 1
        END
    END
    """
    ast = parse_code(code)
    body = ast.statements[0].body
    assert len(body) == 2
    assert isinstance(body[0], WhileStatementNode)
    assert isinstance(body[1], WhileStatementNode)


def test_while_statement_node_methods():
    """Verify WhileStatementNode to_dict, pretty, and repr methods."""
    from ruleflow.ast.nodes import WhileStatementNode, LiteralNode

    while_node = WhileStatementNode(
        condition=LiteralNode(value=True, literal_type="BOOLEAN", line=1, column=7),
        body=[],
        line=1,
        column=1,
    )
    d = while_node.to_dict()
    assert d["node_type"] == "WhileStatementNode"
    assert d["condition"]["value"] is True
    assert d["body"] == []
    assert "WhileStatementNode" in while_node.pretty()
    assert repr(while_node).startswith("WhileStatementNode")


# -------------------------------------------------------------
# 7. User-Defined Functions Tests (Phase 7.4)
# -------------------------------------------------------------

def test_parse_function_single_parameter():
    """Verify parsing a function with a single parameter and return statement."""
    from ruleflow.ast.nodes import FunctionDeclarationNode, ReturnStatementNode

    code = """
    FUNCTION DoubleVal(x: INTEGER) RETURNS INTEGER:
        RETURN x * 2
    END
    """
    ast = parse_code(code)
    assert len(ast.statements) == 1
    func = ast.statements[0]
    assert isinstance(func, FunctionDeclarationNode)
    assert func.name == "DoubleVal"
    assert len(func.parameters) == 1
    assert func.parameters[0].name == "x"
    assert func.parameters[0].data_type == "INTEGER"
    assert func.return_type == "INTEGER"
    assert len(func.body) == 1
    assert isinstance(func.body[0], ReturnStatementNode)


def test_parse_function_multiple_parameters():
    """Verify parsing a function with multiple parameters."""
    from ruleflow.ast.nodes import FunctionDeclarationNode

    code = """
    FUNCTION CalculateBonus(salary: DECIMAL, percentage: DECIMAL) RETURNS DECIMAL:
        bonus = salary * percentage / 100
        RETURN bonus
    END
    """
    ast = parse_code(code)
    func = ast.statements[0]
    assert isinstance(func, FunctionDeclarationNode)
    assert func.name == "CalculateBonus"
    assert len(func.parameters) == 2
    assert func.parameters[0].name == "salary"
    assert func.parameters[0].data_type == "DECIMAL"
    assert func.parameters[1].name == "percentage"
    assert func.parameters[1].data_type == "DECIMAL"
    assert func.return_type == "DECIMAL"
    assert len(func.body) == 2


def test_parse_function_zero_parameters():
    """Verify parsing a function with zero parameters."""
    from ruleflow.ast.nodes import FunctionDeclarationNode

    code = """
    FUNCTION GetDefaultRate() RETURNS DECIMAL:
        RETURN 0.05
    END
    """
    ast = parse_code(code)
    func = ast.statements[0]
    assert isinstance(func, FunctionDeclarationNode)
    assert func.name == "GetDefaultRate"
    assert len(func.parameters) == 0
    assert func.return_type == "DECIMAL"


def test_parse_function_call_in_rule():
    """Verify parsing a function call expression within a rule."""
    from ruleflow.ast.nodes import FunctionDeclarationNode, RuleDeclarationNode, FunctionCallNode

    code = """
    FUNCTION Square(n: INTEGER) RETURNS INTEGER:
        RETURN n * n
    END

    RULE MathRule:
        res = Square(5) + 1
    END
    """
    ast = parse_code(code)
    assert len(ast.statements) == 2
    assert isinstance(ast.statements[0], FunctionDeclarationNode)
    rule = ast.statements[1]
    assert isinstance(rule, RuleDeclarationNode)
    assign = rule.body[0]
    assert isinstance(assign.value, BinaryOpNode)
    assert isinstance(assign.value.left, FunctionCallNode)
    assert assign.value.left.name == "Square"
    assert len(assign.value.left.args) == 1


def test_parse_nested_function_calls():
    """Verify parsing nested function calls."""
    from ruleflow.ast.nodes import FunctionCallNode

    code = """
    RULE CallRule:
        x = Foo(Bar(1, 2), 3)
    END
    """
    ast = parse_code(code)
    rule = ast.statements[0]
    call = rule.body[0].value
    assert isinstance(call, FunctionCallNode)
    assert call.name == "Foo"
    assert len(call.args) == 2
    assert isinstance(call.args[0], FunctionCallNode)
    assert call.args[0].name == "Bar"


def test_parse_function_missing_returns_error():
    """Verify syntax error when RETURNS is missing."""
    code = """
    FUNCTION BadFunc(x: INTEGER):
        RETURN x
    END
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)
    assert "Expected 'RETURNS' keyword" in exc_info.value.message


def test_parse_function_missing_colon_error():
    """Verify syntax error when ':' is missing after return type."""
    code = """
    FUNCTION BadFunc(x: INTEGER) RETURNS INTEGER
        RETURN x
    END
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)
    assert "Expected ':'" in exc_info.value.message


def test_parse_function_missing_param_type_error():
    """Verify syntax error when parameter type is missing."""
    code = """
    FUNCTION BadFunc(x) RETURNS INTEGER:
        RETURN x
    END
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)
    assert "Expected ':' after parameter" in exc_info.value.message


def test_parse_function_missing_end_error():
    """Verify syntax error when END is missing."""
    code = """
    FUNCTION BadFunc(x: INTEGER) RETURNS INTEGER:
        RETURN x
    """
    with pytest.raises(ParserError) as exc_info:
        parse_code(code)
    assert "Expected 'END' to close FUNCTION declaration" in exc_info.value.message


def test_function_ast_nodes_methods():
    """Verify ParameterNode, ReturnStatementNode, and FunctionDeclarationNode methods."""
    from ruleflow.ast.nodes import ParameterNode, ReturnStatementNode, FunctionDeclarationNode, LiteralNode

    param = ParameterNode("rate", "DECIMAL", line=2, column=5)
    p_dict = param.to_dict()
    assert p_dict["node_type"] == "ParameterNode"
    assert p_dict["name"] == "rate"
    assert p_dict["data_type"] == "DECIMAL"
    assert "rate: DECIMAL" in param.pretty()
    assert repr(param).startswith("ParameterNode")

    ret = ReturnStatementNode(LiteralNode(10, "INTEGER", 3, 12), line=3, column=5)
    r_dict = ret.to_dict()
    assert r_dict["node_type"] == "ReturnStatementNode"
    assert "ReturnStatementNode" in ret.pretty()
    assert repr(ret).startswith("ReturnStatementNode")

    func = FunctionDeclarationNode(
        name="Calc",
        parameters=[param],
        return_type="INTEGER",
        body=[ret],
        line=1,
        column=1,
    )
    f_dict = func.to_dict()
    assert f_dict["node_type"] == "FunctionDeclarationNode"
    assert f_dict["name"] == "Calc"
    assert len(f_dict["parameters"]) == 1
    assert "FunctionDeclarationNode: 'Calc'" in func.pretty()
    assert repr(func).startswith("FunctionDeclarationNode")



