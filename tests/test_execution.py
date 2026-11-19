"""Unit tests for RuleFlow Code Generation and Execution (Module 5)."""

from pathlib import Path
import pytest

from ruleflow.lexer import Lexer
from ruleflow.parser import Parser
from ruleflow.semantic import SemanticAnalyzer
from ruleflow.ir import IRGenerator
from ruleflow.optimizer import Optimizer
from ruleflow.codegen import CodeGenerator
from ruleflow.execution import Executor, ExecutionError, TACInterpreter, RuntimeEnvironment
from ruleflow.ir.instructions import (
    AssignInstruction,
    BinaryOpInstruction,
    LabelInstruction,
    JumpInstruction,
    Constant,
)


def run_pipeline(code: str, inputs=None, input_types=None, optimize=True):
    """Compile and execute a RuleFlow code string through the full compiler pipeline."""
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(ast, input_types=input_types)
    analyzer.analyze()

    raw_ir = IRGenerator(ast).generate()
    ir_to_run = Optimizer(raw_ir).optimize() if optimize else raw_ir
    target_code = CodeGenerator(ir_to_run).generate()

    executor = Executor(target_code=target_code, symbol_table=analyzer.symbol_table)
    result = executor.execute(inputs=inputs)
    return result


# -------------------------------------------------------------
# Tests 1-7: Basic Assignments and Expressions
# -------------------------------------------------------------

def test_simple_variable_assignment():
    """Test 1: Simple variable assignments."""
    code = """
    RULE AssignTest:
        x = 42
        y = 100
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["x"] == 42
    assert res.outputs["y"] == 100


def test_arithmetic_operations():
    """Test 2: Basic arithmetic operations (+, -, *, /, %)."""
    code = """
    RULE ArithmeticTest:
        add_res = 10 + 5
        sub_res = 10 - 3
        mul_res = 4 * 6
        div_res = 15 / 3
        mod_res = 17 % 5
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["add_res"] == 15
    assert res.outputs["sub_res"] == 7
    assert res.outputs["mul_res"] == 24
    assert res.outputs["div_res"] == 5.0
    assert res.outputs["mod_res"] == 2


def test_operator_precedence():
    """Test 3: Operator precedence execution."""
    code = """
    RULE PrecedenceTest:
        r1 = 10 + 20 * 2
        r2 = (10 + 20) * 2
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["r1"] == 50
    assert res.outputs["r2"] == 60


def test_string_assignments():
    """Test 4: String assignments and equality."""
    code = """
    RULE StringTest:
        greeting = "Welcome"
        is_same = greeting == "Welcome"
        is_diff = greeting != "Hello"
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["greeting"] == "Welcome"
    assert res.outputs["is_same"] is True
    assert res.outputs["is_diff"] is True


def test_boolean_operations():
    """Test 5: Boolean logic execution."""
    code = """
    RULE BoolTest:
        t = 10 > 5
        f = 2 > 10
        b_and = t AND f
        b_or = t OR f
        b_not = NOT f
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["b_and"] is False
    assert res.outputs["b_or"] is True
    assert res.outputs["b_not"] is True


def test_relational_operations():
    """Test 6: Relational comparisons (<, <=, >, >=, ==, !=)."""
    code = """
    RULE RelTest:
        c1 = 5 < 10
        c2 = 10 <= 10
        c3 = 15 > 20
        c4 = 20 >= 20
        c5 = 7 == 7
        c6 = 8 != 8
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["c1"] is True
    assert res.outputs["c2"] is True
    assert res.outputs["c3"] is False
    assert res.outputs["c4"] is True
    assert res.outputs["c5"] is True
    assert res.outputs["c6"] is False


def test_unary_operations():
    """Test 7: Unary plus and minus."""
    code = """
    RULE UnaryTest:
        a = 15
        neg = -a
        pos = +a
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["neg"] == -15
    assert res.outputs["pos"] == 15


# -------------------------------------------------------------
# Tests 8-13: Control Flow and Conditionals
# -------------------------------------------------------------

def test_if_condition_evaluates_to_true():
    """Test 8: IF condition evaluates to true."""
    code = """
    RULE IfTrueTest:
        x = 10
        IF x > 5 THEN
            result = "Passed"
        END
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["result"] == "Passed"


def test_if_condition_evaluates_to_false():
    """Test 9: IF condition evaluates to false (without else)."""
    code = """
    RULE IfFalseTest:
        x = 2
        result = "Initial"
        IF x > 5 THEN
            result = "Modified"
        END
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["result"] == "Initial"


def test_if_else_execution():
    """Test 10: IF-ELSE branch selection."""
    code = """
    RULE IfElseTest:
        IF val > 50 THEN
            branch = "Then"
        ELSE
            branch = "Else"
        END
    END
    """
    # Test True path
    r_then = run_pipeline(code, inputs={"val": 75}, input_types={"val": "INTEGER"})
    assert r_then.status == "success"
    assert r_then.outputs["branch"] == "Then"

    # Test False path
    r_else = run_pipeline(code, inputs={"val": 25}, input_types={"val": "INTEGER"})
    assert r_else.status == "success"
    assert r_else.outputs["branch"] == "Else"


def test_nested_if_conditions():
    """Test 11: Nested IF conditions."""
    code = """
    RULE NestedTest:
        IF score >= 50 THEN
            IF score >= 90 THEN
                grade = "A"
            ELSE
                grade = "B"
            END
        ELSE
            grade = "F"
        END
    END
    """
    r_a = run_pipeline(code, inputs={"score": 95}, input_types={"score": "INTEGER"})
    assert r_a.outputs["grade"] == "A"

    r_b = run_pipeline(code, inputs={"score": 75}, input_types={"score": "INTEGER"})
    assert r_b.outputs["grade"] == "B"

    r_f = run_pipeline(code, inputs={"score": 40}, input_types={"score": "INTEGER"})
    assert r_f.outputs["grade"] == "F"


def test_and_or_short_circuit_execution():
    """Test 12: AND / OR short-circuit control flow execution."""
    code = """
    RULE ShortCircuitTest:
        r1 = (10 > 5) OR (100 / zero == 1)
        r2 = (2 > 10) AND (50 / zero == 1)
    END
    """
    # If not short-circuited, runtime division by zero would occur.
    # Because of short-circuiting, r1 is True without evaluating the second term,
    # and r2 is False without evaluating the second term!
    # Run unoptimized so short-circuit branches are executed dynamically:
    res = run_pipeline(code, input_types={"zero": "INTEGER"}, inputs={"zero": 0}, optimize=False)
    assert res.status == "success"
    assert res.outputs["r1"] is True
    assert res.outputs["r2"] is False


def test_multiple_rules_execution():
    """Test 13: Multiple rules executed sequentially."""
    code = """
    RULE RuleA:
        a = 10
        total_a = a * 2
    END

    RULE RuleB:
        b = 20
        total_b = b * 3
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["total_a"] == 20
    assert res.outputs["total_b"] == 60


# -------------------------------------------------------------
# Tests 14-20: Errors, Validation, and Safety
# -------------------------------------------------------------

def test_missing_external_inputs():
    """Test 14: Execution fails with clear error when required external input is missing."""
    code = """
    RULE InputCheck:
        IF score >= 50 THEN
            res = "Pass"
        ELSE
            res = "Fail"
        END
    END
    """
    # Supply empty inputs dictionary
    res = run_pipeline(code, inputs={}, input_types={"score": "INTEGER"})
    assert res.status == "failed"
    assert "Missing required external input: 'score'" in res.error


def test_invalid_external_input_types():
    """Test 15: Execution fails when external input has wrong runtime type."""
    code = """
    RULE TypeCheck:
        IF count > 0 THEN
            res = 1
        ELSE
            res = 0
        END
    END
    """
    # count is declared INTEGER, but string passed
    res = run_pipeline(code, inputs={"count": "ten"}, input_types={"count": "INTEGER"})
    assert res.status == "failed"
    assert "Invalid input type for 'count'" in res.error


def test_division_by_zero_runtime():
    """Test 16: Division by zero raises ExecutionError at runtime."""
    # Dynamic division by zero (variable denominator)
    code = """
    RULE DivZeroDynamic:
        x = 100
        y = 0
        ans = x / y
    END
    """
    res = run_pipeline(code, optimize=False)
    assert res.status == "failed"
    assert "Division by zero" in res.error


def test_modulo_by_zero_runtime():
    """Test 17: Modulo by zero raises ExecutionError at runtime."""
    code = """
    RULE ModZeroDynamic:
        x = 100
        y = 0
        ans = x % y
    END
    """
    res = run_pipeline(code, optimize=False)
    assert res.status == "failed"
    assert "Modulo by zero" in res.error


def test_undefined_variable_handling():
    """Test 18: Interpreter raises ExecutionError on reading undefined variable."""
    raw_ir = [
        AssignInstruction("x", "missing_var"),
    ]
    interp = TACInterpreter(raw_ir)
    res = interp.execute()
    assert res.status == "failed"
    assert "Variable 'missing_var' is undefined" in res.error


def test_execution_step_limit():
    """Test 19: Infinite loops or long executions trigger step limit."""
    # Create an artificial infinite loop using TAC jumps
    raw_ir = [
        LabelInstruction("LOOP"),
        AssignInstruction("x", Constant(1)),
        JumpInstruction("LOOP"),
    ]
    interp = TACInterpreter(raw_ir, max_steps=50)
    res = interp.execute()
    assert res.status == "failed"
    assert "Execution step limit exceeded" in res.error


def test_named_outputs_do_not_contain_temporaries():
    """Test 20: Outputs contain user variables (result, base, etc.), not t1, t2."""
    code = """
    RULE TempFilter:
        result = 10 + 20 * 2
        total = result + 5
    END
    """
    res = run_pipeline(code, optimize=False)
    assert res.status == "success"
    # Ensure no temporary variable is in outputs
    for key in res.outputs:
        assert not key.startswith("t") or not key[1:].isdigit()
    assert "result" in res.outputs
    assert "total" in res.outputs


def test_optimized_and_unoptimized_equivalence():
    """Test 21: Optimized and unoptimized IR produce identical outputs."""
    code = """
    RULE EquivTest:
        result = 10 + 20 * 2
        base = 100
        total = base + 50
    END
    """
    res_unopt = run_pipeline(code, optimize=False)
    res_opt = run_pipeline(code, optimize=True)

    assert res_unopt.status == "success"
    assert res_opt.status == "success"
    assert res_unopt.outputs == res_opt.outputs


# -------------------------------------------------------------
# Tests 22-23: End-to-End Capstone Verification
# -------------------------------------------------------------

def test_student_eligibility_eligible():
    """Test 22: StudentEligibility capstone program with eligible inputs."""
    file_path = Path(__file__).parent.parent / "examples" / "student_eligibility.rf"
    code = file_path.read_text(encoding="utf-8")

    res = run_pipeline(
        code,
        inputs={"gpa": 3.8, "attendance": 85},
        input_types={"gpa": "DECIMAL", "attendance": "INTEGER"},
    )
    assert res.status == "success"
    assert res.outputs["status"] == "Eligible"


def test_student_eligibility_ineligible():
    """Test 23: StudentEligibility capstone program with ineligible inputs."""
    file_path = Path(__file__).parent.parent / "examples" / "student_eligibility.rf"
    code = file_path.read_text(encoding="utf-8")

    res = run_pipeline(
        code,
        inputs={"gpa": 2.8, "attendance": 90},
        input_types={"gpa": "DECIMAL", "attendance": "INTEGER"},
    )
    assert res.status == "success"
    assert res.outputs["status"] == "Not Eligible"


def test_calculation_example():
    """Test Calculation example from specification."""
    code = """
    RULE Calculation:
        result = 10 + 20 * 2
        base = 100
        total = base + 50
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs["result"] == 50
    assert res.outputs["base"] == 100
    assert res.outputs["total"] == 150


def test_sample_rule_score_90():
    """Regression Test: SampleRule program with score = 90 without ELSE."""
    code = """
    RULE SampleRule:
        IF score >= 80 THEN
            status = "Approved"
        END
    END
    """
    res = run_pipeline(
        code,
        inputs={"score": 90},
        input_types={"score": "INTEGER"},
    )
    assert res.status == "success"
    assert res.outputs["score"] == 90
    assert res.outputs["status"] == "Approved"
    assert res.steps > 0
    assert res.step_count == res.steps
    assert res["steps"] == res.steps


def test_sample_rule_with_else_branch():
    """Regression Test: SampleRule program with ELSE branch (score = 70 and score = 90)."""
    code = """
    RULE SampleRule:
        IF score >= 80 THEN
            status = "Approved"
        ELSE
            status = "Rejected"
        END
    END
    """
    # 1. Test score = 70 (ineligible, triggers ELSE branch)
    res_70 = run_pipeline(
        code,
        inputs={"score": 70},
        input_types={"score": "INTEGER"},
    )
    assert res_70.status == "success"
    assert res_70.outputs["score"] == 70
    assert res_70.outputs["status"] == "Rejected"
    assert res_70.steps > 0
    assert res_70.step_count == res_70.steps

    # 2. Test score = 90 (eligible, triggers THEN branch)
    res_90 = run_pipeline(
        code,
        inputs={"score": 90},
        input_types={"score": "INTEGER"},
    )
    assert res_90.status == "success"
    assert res_90.outputs["score"] == 90
    assert res_90.outputs["status"] == "Approved"
    assert res_90.steps > 0
    assert res_90.step_count == res_90.steps


# -------------------------------------------------------------
# Tests 27-29: Empty, Comment-only, and No-op Programs
# -------------------------------------------------------------

def test_empty_source_code_execution():
    """End-to-end test: Empty source code returns ready status with 0 steps."""
    res = run_pipeline("")
    assert res.status == "ready"
    assert res.outputs == {}
    assert res.steps == 0
    assert res.step_count == 0
    assert res.error is None


def test_comment_only_source_code_execution():
    """End-to-end test: Comment-only source code returns ready status with 0 steps."""
    code = """
    // Only comments in this file
    // Line 2 comment
    """
    res = run_pipeline(code)
    assert res.status == "ready"
    assert res.outputs == {}
    assert res.steps == 0
    assert res.step_count == 0
    assert res.error is None


def test_program_with_no_executable_instructions():
    """End-to-end test: Program that parses successfully but contains no assignments or computations."""
    code = """
    RULE EmptyRule:
    END
    """
    res = run_pipeline(code)
    assert res.status == "success"
    assert res.outputs == {}
    assert res.steps > 0
    assert res.error is None
