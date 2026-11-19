"""Comprehensive unit tests for RuleFlow Semantic Analysis (Module 3)."""

from pathlib import Path
import pytest

from ruleflow.lexer import Lexer
from ruleflow.parser import Parser
from ruleflow.semantic import SemanticAnalyzer, SemanticError, DataType


def parse_and_analyze(code: str, input_types=None):
    """Helper to tokenize, parse, and semantically analyze code."""
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(ast=ast, input_types=input_types)
    analyzer.analyze()
    return analyzer


# -------------------------------------------------------------
# 1. Valid Programs and Type Inference Tests
# -------------------------------------------------------------

def test_valid_program_with_integer_and_decimal_inputs():
    """Test 1: Valid program with INTEGER and DECIMAL inputs."""
    code = """
    RULE ScoreCalculation:
        bonus = 10
        total = score + bonus + factor
    """
    analyzer = parse_and_analyze(
        code,
        input_types={"score": DataType.INTEGER, "factor": DataType.DECIMAL},
    )
    table = analyzer.current_symbol_table
    assert table is not None
    assert table.lookup("score").data_type == DataType.INTEGER
    assert table.lookup("factor").data_type == DataType.DECIMAL
    assert table.lookup("bonus").data_type == DataType.INTEGER
    assert table.lookup("total").data_type == DataType.DECIMAL


def test_valid_numeric_comparison():
    """Test 2: Valid numeric comparison producing BOOLEAN."""
    code = """
    RULE CompareRule:
        is_high = score >= 50.5
        is_low = count < 10
        is_same = count == score
    """
    analyzer = parse_and_analyze(
        code,
        input_types={"score": DataType.INTEGER, "count": DataType.INTEGER},
    )
    table = analyzer.current_symbol_table
    assert table.lookup("is_high").data_type == DataType.BOOLEAN
    assert table.lookup("is_low").data_type == DataType.BOOLEAN
    assert table.lookup("is_same").data_type == DataType.BOOLEAN


def test_valid_boolean_and_or_expressions():
    """Test 3: Valid BOOLEAN AND/OR expressions."""
    code = """
    RULE LogicRule:
        cond1 = x > 10
        cond2 = y <= 20
        combined = cond1 AND cond2 OR NOT cond1
    """
    analyzer = parse_and_analyze(
        code,
        input_types={"x": DataType.INTEGER, "y": DataType.INTEGER},
    )
    table = analyzer.current_symbol_table
    assert table.lookup("combined").data_type == DataType.BOOLEAN


def test_valid_integer_to_decimal_widening():
    """Test 10: Valid INTEGER-to-DECIMAL widening on assignment."""
    code = """
    RULE WideningRule:
        rate = 4.5
        rate = 2
    """
    analyzer = parse_and_analyze(code)
    table = analyzer.current_symbol_table
    assert table.lookup("rate").data_type == DataType.DECIMAL


def test_variable_assigned_in_both_branches_and_used_afterward():
    """Test 12: Variable assigned in both branches and used afterward."""
    code = """
    RULE BranchBoth:
        IF x > 0 THEN
            val = 100
        ELSE
            val = 200
        END
        final_val = val + 50
    """
    analyzer = parse_and_analyze(code, input_types={"x": DataType.INTEGER})
    table = analyzer.current_symbol_table
    assert table.lookup("val").data_type == DataType.INTEGER
    assert table.lookup("final_val").data_type == DataType.INTEGER


def test_variable_scope_isolation_between_rules():
    """Test 14: Variable scope isolation between rules."""
    code = """
    RULE FirstRule:
        temp = 42

    RULE SecondRule:
        other = 100
    """
    analyzer = parse_and_analyze(code)
    assert "FirstRule" in analyzer.symbol_tables
    assert "SecondRule" in analyzer.symbol_tables
    assert analyzer.symbol_tables["FirstRule"].is_defined("temp")
    assert not analyzer.symbol_tables["SecondRule"].is_defined("temp")
    assert analyzer.symbol_tables["SecondRule"].is_defined("other")


# -------------------------------------------------------------
# 2. Semantic Error Handling Tests
# -------------------------------------------------------------

def test_numeric_and_string_type_mismatch():
    """Test 4: Numeric and string type mismatch in equality/comparison."""
    code = """
    RULE MismatchRule:
        flag = 10 == "ten"
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)

    assert "Type mismatch: cannot compare INTEGER with STRING" in exc_info.value.message


def test_undefined_variable():
    """Test 5: Undefined variable usage raises SemanticError."""
    code = """
    RULE UndefinedRule:
        res = unknown_var + 5
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)

    assert "Undefined variable 'unknown_var'" in exc_info.value.message


def test_invalid_arithmetic_with_a_string():
    """Test 6: Invalid arithmetic operation with a STRING."""
    code = """
    RULE BadArithmetic:
        res = "hello" + 5
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)

    assert "Arithmetic operator '+' requires numeric operands" in exc_info.value.message


def test_invalid_logical_operation_with_a_numeric_operand():
    """Test 7: Invalid logical operation with a numeric operand."""
    code = """
    RULE BadLogic:
        flag = 10 AND (x > 5)
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code, input_types={"x": DataType.INTEGER})

    assert "Operator AND requires BOOLEAN operands" in exc_info.value.message


def test_non_boolean_if_condition():
    """Test 8: Non-BOOLEAN IF condition."""
    code = """
    RULE BadCondition:
        IF 42 THEN
            y = 1
        END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)

    assert "IF condition must evaluate to BOOLEAN, got INTEGER" in exc_info.value.message


def test_incompatible_reassignment():
    """Test 9: Incompatible reassignment (e.g. assigning STRING to INTEGER)."""
    code = """
    RULE IncompatibleAssign:
        age = 25
        age = "twenty-five"
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)

    assert "Cannot assign STRING to INTEGER variable 'age'" in exc_info.value.message


def test_division_by_literal_zero():
    """Test 11: Division or modulo by a literal zero detected statically."""
    code = """
    RULE DivZero:
        x = 100 / 0
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)

    assert "Division by zero detected" in exc_info.value.message

    code_mod = """
    RULE ModZero:
        y = 50 % 0.0
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code_mod)

    assert "Modulo by zero detected" in exc_info.value.message


def test_variable_assigned_in_only_one_branch_and_used_afterward():
    """Test 13: Variable assigned in only one branch and used afterward."""
    code = """
    RULE OneBranch:
        IF x > 5 THEN
            res = 10
        END
        final_val = res + 1
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code, input_types={"x": DataType.INTEGER})

    assert "Undefined variable 'res'" in exc_info.value.message

    # Also test when assigned in THEN but not in ELSE
    code_unequal_branches = """
    RULE UnequalBranches:
        IF x > 5 THEN
            res = 10
        ELSE
            other = 20
        END
        final_val = res + 1
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code_unequal_branches, input_types={"x": DataType.INTEGER})

    assert "Undefined variable 'res'" in exc_info.value.message


def test_variable_leak_between_rules_error():
    """Test 14b: Using variable from earlier rule in a subsequent rule raises error."""
    code = """
    RULE FirstRule:
        temp = 42

    RULE SecondRule:
        other = temp + 1
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)

    assert "Undefined variable 'temp'" in exc_info.value.message


# -------------------------------------------------------------
# 3. Student Eligibility Capstone Analysis Test
# -------------------------------------------------------------

def test_student_eligibility_semantic_analysis():
    """Test analyzing examples/student_eligibility.rf with gpa: DECIMAL and attendance: INTEGER."""
    file_path = Path(__file__).parent.parent / "examples" / "student_eligibility.rf"
    code = file_path.read_text(encoding="utf-8")

    analyzer = parse_and_analyze(
        code,
        input_types={"gpa": "DECIMAL", "attendance": "INTEGER"},
    )

    table = analyzer.symbol_tables.get("StudentEligibility")
    assert table is not None

    # Check external input variables
    gpa_sym = table.lookup("gpa")
    assert gpa_sym is not None
    assert gpa_sym.data_type == DataType.DECIMAL
    assert gpa_sym.is_input is True

    att_sym = table.lookup("attendance")
    assert att_sym is not None
    assert att_sym.data_type == DataType.INTEGER
    assert att_sym.is_input is True

    # Check definitely assigned internal variable 'status'
    status_sym = table.lookup("status")
    assert status_sym is not None
    assert status_sym.data_type == DataType.STRING
    assert status_sym.is_input is False


# -------------------------------------------------------------
# 4. ELSE IF Semantic Tests
# -------------------------------------------------------------

def test_semantic_non_boolean_else_if_condition():
    """Verify semantic error when an ELSE IF condition is not BOOLEAN."""
    code = """
    RULE BadElifCond:
        IF x > 10 THEN
            y = 1
        ELSE IF 42 + 5 THEN
            y = 2
        ELSE
            y = 3
        END
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code, input_types={"x": "INTEGER"})
    assert "ELSE IF condition must evaluate to BOOLEAN, got INTEGER" in exc_info.value.message


def test_semantic_definite_assignment_across_all_else_if_branches():
    """Verify variable assigned in IF, all ELSE IFs, and ELSE is definitely assigned afterward."""
    code = """
    RULE DefiniteAssignElif:
        IF score >= 90 THEN
            grade = "A"
        ELSE IF score >= 75 THEN
            grade = "B"
        ELSE IF score >= 60 THEN
            grade = "C"
        ELSE
            grade = "F"
        END
        final_grade = grade
    END
    """
    analyzer = parse_and_analyze(code, input_types={"score": "INTEGER"})
    table = analyzer.symbol_tables["DefiniteAssignElif"]
    assert table.is_defined("grade")
    assert table.is_defined("final_grade")
    assert table.lookup("grade").data_type == DataType.STRING


def test_semantic_variable_assigned_in_only_some_else_if_branches_error():
    """Verify error when a variable assigned in only some ELSE IF branches is used afterward."""
    code = """
    RULE PartialAssignElif:
        IF score >= 90 THEN
            grade = "A"
            bonus = 10
        ELSE IF score >= 75 THEN
            grade = "B"
        ELSE
            grade = "F"
            bonus = 0
        END
        result = bonus + 1
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code, input_types={"score": "INTEGER"})
    assert "Undefined variable 'bonus'" in exc_info.value.message


def test_semantic_incompatible_types_across_else_if_branches_error():
    """Verify error when variable is assigned incompatible types across ELSE IF branches."""
    code = """
    RULE IncompatibleElif:
        IF score >= 90 THEN
            res = "Excellent"
        ELSE IF score >= 75 THEN
            res = 100
        ELSE
            res = "Try Again"
        END
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code, input_types={"score": "INTEGER"})
    assert "assigned with incompatible types across branches" in exc_info.value.message


# -------------------------------------------------------------
# 5. Built-in Function Semantic Analysis Tests (Phase 7.2)
# -------------------------------------------------------------

def test_semantic_builtin_functions_valid():
    """Verify semantic validation and type inference for valid built-in function calls."""
    code = """
    RULE BuiltinsValid:
        a = ABS(-10)
        b = ABS(-3.14)
        c = MIN(10, 20)
        d = MIN(10, 20.5)
        e = MAX(10, 20)
        f = MAX(10.5, 20)
        g = ROUND(12.6)
        h = ROUND(10)
        i = LENGTH("RuleFlow")
        j = LENGTH(user_name)
    END
    """
    analyzer = parse_and_analyze(code, input_types={"user_name": "STRING"})
    symtab = analyzer.current_symbol_table
    assert symtab is not None
    assert symtab.lookup("a").data_type == DataType.INTEGER
    assert symtab.lookup("b").data_type == DataType.DECIMAL
    assert symtab.lookup("c").data_type == DataType.INTEGER
    assert symtab.lookup("d").data_type == DataType.DECIMAL
    assert symtab.lookup("e").data_type == DataType.INTEGER
    assert symtab.lookup("f").data_type == DataType.DECIMAL
    assert symtab.lookup("g").data_type == DataType.INTEGER
    assert symtab.lookup("h").data_type == DataType.INTEGER
    assert symtab.lookup("i").data_type == DataType.INTEGER
    assert symtab.lookup("j").data_type == DataType.INTEGER


def test_semantic_unknown_function_error():
    """Verify error on unknown function call."""
    code = """
    RULE BadFunction:
        x = SQRT(16)
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Unknown function 'SQRT'" in exc_info.value.message


def test_semantic_function_arg_count_error():
    """Verify error when function is called with incorrect argument count."""
    code1 = """
    RULE BadArgCount1:
        x = ABS(1, 2)
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code1)
    assert "Function 'ABS' requires exactly 1 argument" in exc_info.value.message

    code2 = """
    RULE BadArgCount2:
        x = MIN(10)
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code2)
    assert "Function 'MIN' requires exactly 2 argument" in exc_info.value.message


def test_semantic_function_arg_type_errors():
    """Verify error when function is called with incompatible argument types."""
    # ABS with STRING
    code1 = """
    RULE BadAbs:
        x = ABS("test")
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code1)
    assert "requires a numeric argument" in exc_info.value.message

    # LENGTH with INTEGER
    code2 = """
    RULE BadLen:
        x = LENGTH(42)
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code2)
    assert "requires a STRING argument" in exc_info.value.message

    # ROUND with STRING
    code3 = """
    RULE BadRound:
        x = ROUND("3.14")
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code3)
    assert "requires a numeric argument" in exc_info.value.message

    # MIN with non-numeric
    code4 = """
    RULE BadMin:
        x = MIN("a", 10)
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code4)
    assert "requires numeric arguments" in exc_info.value.message

