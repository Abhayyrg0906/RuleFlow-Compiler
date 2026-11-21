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


# -------------------------------------------------------------
# 6. WHILE Loop Semantic Analysis Tests (Phase 7.3)
# -------------------------------------------------------------

def test_semantic_while_boolean_condition_valid():
    """Verify semantic validation of valid boolean conditions in WHILE loops."""
    code = """
    RULE WhileValid:
        count = 5
        WHILE count > 0 DO
            count = count - 1
        END
        final_count = count
    END
    """
    analyzer = parse_and_analyze(code)
    table = analyzer.current_symbol_table
    assert table.lookup("count").data_type == DataType.INTEGER
    assert table.lookup("final_count").data_type == DataType.INTEGER


def test_semantic_while_numeric_condition_rejected():
    """Verify that a numeric condition in WHILE loop raises a SemanticError."""
    code = """
    RULE BadCondition:
        WHILE 10 DO
            x = 1
        END
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "WHILE condition must evaluate to BOOLEAN, got INTEGER" in exc_info.value.message


def test_semantic_while_undefined_variable_in_condition_rejected():
    """Verify that an undefined variable in a WHILE condition raises a SemanticError."""
    code = """
    RULE UndefinedCond:
        WHILE missing_counter > 0 DO
            x = 1
        END
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Undefined variable 'missing_counter'" in exc_info.value.message


def test_semantic_while_incompatible_assignment_rejected():
    """Verify that assigning an incompatible type inside a WHILE loop raises a SemanticError."""
    code = """
    RULE BadAssignInWhile:
        count = 10
        WHILE count > 0 DO
            count = "invalid string"
        END
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Cannot assign STRING to INTEGER variable 'count'" in exc_info.value.message


def test_semantic_while_definite_assignment_not_guaranteed():
    """Verify that variables assigned solely inside a WHILE loop are not definitely assigned afterward."""
    code = """
    RULE IndefiniteAssign:
        count = 5
        WHILE count > 0 DO
            loop_var = 100
            count = count - 1
        END
        out = loop_var
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Undefined variable 'loop_var'" in exc_info.value.message


def test_semantic_while_prior_variable_remains_available():
    """Verify that variables assigned before a WHILE loop remain available and typed after the loop."""
    code = """
    RULE PriorVarValid:
        total = 0
        count = 5
        WHILE count > 0 DO
            total = total + count
            count = count - 1
        END
        result = total + count
    END
    """
    analyzer = parse_and_analyze(code)
    table = analyzer.current_symbol_table
    assert table.lookup("total").data_type == DataType.INTEGER
    assert table.lookup("count").data_type == DataType.INTEGER
    assert table.lookup("result").data_type == DataType.INTEGER


def test_semantic_while_builtin_function_in_condition():
    """Verify that built-in function calls work properly within WHILE conditions."""
    code = """
    RULE BuiltinInWhile:
        diff = -10
        WHILE ABS(diff) > 0 DO
            diff = diff + 1
        END
    END
    """
    analyzer = parse_and_analyze(code)
    table = analyzer.current_symbol_table
    assert table.lookup("diff").data_type == DataType.INTEGER


# -------------------------------------------------------------
# 11. User-Defined Functions Semantic Tests (Phase 7.4)
# -------------------------------------------------------------

def test_semantic_valid_function_declaration_and_call():
    """Verify semantic validation of a valid function and its call in a rule."""
    code = """
    FUNCTION DoubleVal(x: INTEGER) RETURNS INTEGER:
        res = x * 2
        RETURN res
    END

    RULE Compute:
        a = DoubleVal(10)
    END
    """
    analyzer = parse_and_analyze(code)
    assert "DoubleVal" in analyzer.function_symbols
    func_sym = analyzer.function_symbols["DoubleVal"]
    assert func_sym.return_type == DataType.INTEGER
    assert len(func_sym.parameters) == 1
    assert func_sym.parameters[0] == ("x", DataType.INTEGER)
    assert analyzer.current_symbol_table.lookup("a").data_type == DataType.INTEGER


def test_semantic_duplicate_function_name_rejected():
    """Verify rejection of duplicate function definitions."""
    code = """
    FUNCTION Foo() RETURNS INTEGER:
        RETURN 1
    END

    FUNCTION Foo() RETURNS INTEGER:
        RETURN 2
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Duplicate function name 'Foo'" in exc_info.value.message


def test_semantic_builtin_collision_rejected():
    """Verify that user-defined functions cannot shadow built-in functions."""
    code = """
    FUNCTION ABS(x: INTEGER) RETURNS INTEGER:
        RETURN x
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "conflicts with built-in function" in exc_info.value.message


def test_semantic_duplicate_parameter_rejected():
    """Verify rejection of duplicate parameter names in function declaration."""
    code = """
    FUNCTION Add(a: INTEGER, a: INTEGER) RETURNS INTEGER:
        RETURN a + a
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Duplicate parameter 'a'" in exc_info.value.message


def test_semantic_invalid_parameter_or_return_type():
    """Verify rejection of unknown parameter or return types."""
    code = """
    FUNCTION Bad(a: UNKNOWN_TYPE) RETURNS INTEGER:
        RETURN 1
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Invalid type 'UNKNOWN_TYPE'" in exc_info.value.message


def test_semantic_missing_return_statement():
    """Verify rejection of a function with no RETURN statement."""
    code = """
    FUNCTION NoReturn(x: INTEGER) RETURNS INTEGER:
        y = x + 1
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "missing a RETURN statement" in exc_info.value.message


def test_semantic_multiple_return_statements_rejected():
    """Verify rejection of multiple or non-terminal return statements."""
    code = """
    FUNCTION MultiReturn(x: INTEGER) RETURNS INTEGER:
        RETURN x
        y = 10
        RETURN y
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Multiple or conditional return paths" in exc_info.value.message


def test_semantic_incompatible_return_type():
    """Verify error when returned expression doesn't match declared return type."""
    code = """
    FUNCTION BadReturn() RETURNS INTEGER:
        RETURN "not an integer"
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "incompatible type STRING" in exc_info.value.message


def test_semantic_integer_to_decimal_widening_return():
    """Verify that returning an INTEGER for a DECIMAL function is permitted via widening."""
    code = """
    FUNCTION GetDec() RETURNS DECIMAL:
        RETURN 42
    END

    RULE CheckDec:
        v = GetDec()
    END
    """
    analyzer = parse_and_analyze(code)
    assert analyzer.current_symbol_table.lookup("v").data_type == DataType.DECIMAL


def test_semantic_integer_to_decimal_widening_argument():
    """Verify that passing an INTEGER argument to a DECIMAL parameter is permitted via widening."""
    code = """
    FUNCTION Half(val: DECIMAL) RETURNS DECIMAL:
        RETURN val / 2.0
    END

    RULE WideningArg:
        res = Half(10)
    END
    """
    analyzer = parse_and_analyze(code)
    assert analyzer.current_symbol_table.lookup("res").data_type == DataType.DECIMAL


def test_semantic_wrong_argument_count():
    """Verify error when function call passes incorrect number of arguments."""
    code = """
    FUNCTION Add(a: INTEGER, b: INTEGER) RETURNS INTEGER:
        RETURN a + b
    END

    RULE CallAdd:
        x = Add(1)
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Function 'Add' expects 2 argument(s), got 1" in exc_info.value.message


def test_semantic_wrong_argument_type():
    """Verify error when argument type cannot be converted to parameter type."""
    code = """
    FUNCTION Multiply(a: INTEGER, b: INTEGER) RETURNS INTEGER:
        RETURN a * b
    END

    RULE CallMul:
        x = Multiply(10, "string")
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "parameter 'b' expected INTEGER, got STRING" in exc_info.value.message


def test_semantic_unknown_function_call():
    """Verify error when calling an undefined function."""
    code = """
    RULE UnknownCall:
        x = NonExistent(123)
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Unknown function 'NonExistent'" in exc_info.value.message


def test_semantic_function_local_scope_cannot_leak():
    """Verify that variables defined inside a function cannot be accessed outside."""
    code = """
    FUNCTION Helper() RETURNS INTEGER:
        secret_var = 999
        RETURN secret_var
    END

    RULE RuleA:
        res = Helper()
        bad = secret_var
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Undefined variable 'secret_var'" in exc_info.value.message


def test_semantic_function_cannot_read_rule_variables():
    """Verify that variables defined in a rule are not accessible inside a function."""
    code = """
    FUNCTION Broken() RETURNS INTEGER:
        RETURN rule_level_var + 1
    END

    RULE RuleB:
        rule_level_var = 100
        res = Broken()
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Undefined variable 'rule_level_var'" in exc_info.value.message


def test_semantic_reject_self_recursion():
    """Verify that recursive function calls are rejected."""
    code = """
    FUNCTION Factorial(n: INTEGER) RETURNS INTEGER:
        ans = Factorial(n - 1)
        RETURN ans
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Recursive function call to 'Factorial' is not supported" in exc_info.value.message


def test_semantic_reject_forward_declaration_or_mutual_calls():
    """Verify that forward calls or mutual recursion are rejected due to declaration order."""
    code = """
    FUNCTION Alpha(x: INTEGER) RETURNS INTEGER:
        RETURN Beta(x)
    END

    FUNCTION Beta(x: INTEGER) RETURNS INTEGER:
        RETURN Alpha(x)
    END
    """
    with pytest.raises(SemanticError) as exc_info:
        parse_and_analyze(code)
    assert "Unknown function 'Beta'" in exc_info.value.message


def test_semantic_function_symbol_class():
    """Verify FunctionSymbol attributes, dictionary conversion, and representation."""
    from ruleflow.semantic.symbol_table import FunctionSymbol

    sym = FunctionSymbol(
        name="Compute",
        parameters=[("val", DataType.INTEGER)],
        return_type=DataType.DECIMAL,
        line=5,
        column=1,
    )
    assert sym.name == "Compute"
    assert sym.return_type == DataType.DECIMAL
    assert sym.parameters[0] == ("val", DataType.INTEGER)
    d = sym.to_dict()
    assert d["name"] == "Compute"
    assert d["return_type"] == "DECIMAL"
    assert d["parameters"] == [{"name": "val", "type": "INTEGER"}]
    assert repr(sym).startswith("FunctionSymbol")



