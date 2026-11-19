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


def run_pipeline(code: str, inputs=None, input_types=None, optimize=True, max_steps=10000):
    """Compile and execute a RuleFlow code string through the full compiler pipeline."""
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(ast, input_types=input_types)
    analyzer.analyze()

    raw_ir = IRGenerator(ast).generate()
    ir_to_run = Optimizer(raw_ir).optimize() if optimize else raw_ir
    target_code = CodeGenerator(ir_to_run).generate()

    executor = Executor(
        target_code=target_code,
        symbol_table=analyzer.symbol_table,
        max_steps=max_steps,
    )
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


# -------------------------------------------------------------
# Tests 30-35: ELSE IF Execution Tests
# -------------------------------------------------------------

def test_execution_single_else_if_branch():
    """Test 30: Execution with a single ELSE IF branch."""
    code = """
    RULE SingleElif:
        IF x > 10 THEN
            y = 1
        ELSE IF x > 5 THEN
            y = 2
        ELSE
            y = 3
        END
    END
    """
    # x = 7 -> triggers ELSE IF branch
    res = run_pipeline(code, inputs={"x": 7}, input_types={"x": "INTEGER"})
    assert res.status == "success"
    assert res.outputs["y"] == 2


def test_execution_multiple_else_if_all_paths():
    """Test 31: Execution of multi-branch ELSE IF covering first, middle, last, and ELSE paths."""
    code = """
    RULE MultiPath:
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
    # 1. First condition true (marks = 95 -> A)
    r1 = run_pipeline(code, inputs={"marks": 95}, input_types={"marks": "INTEGER"})
    assert r1.status == "success"
    assert r1.outputs["grade"] == "A"

    # 2. Middle condition true (marks = 80 -> B)
    r2 = run_pipeline(code, inputs={"marks": 80}, input_types={"marks": "INTEGER"})
    assert r2.status == "success"
    assert r2.outputs["grade"] == "B"

    # 3. Last condition true (marks = 65 -> C)
    r3 = run_pipeline(code, inputs={"marks": 65}, input_types={"marks": "INTEGER"})
    assert r3.status == "success"
    assert r3.outputs["grade"] == "C"

    # 4. All conditions false (marks = 45 -> F)
    r4 = run_pipeline(code, inputs={"marks": 45}, input_types={"marks": "INTEGER"})
    assert r4.status == "success"
    assert r4.outputs["grade"] == "F"


def test_execution_else_if_without_else():
    """Test 32: Execution of ELSE IF branches without a final ELSE."""
    code = """
    RULE NoFinalElse:
        flag = 0
        IF val == 1 THEN
            flag = 10
        ELSE IF val == 2 THEN
            flag = 20
        END
    END
    """
    # 1. Matching second condition (val = 2 -> flag = 20)
    r1 = run_pipeline(code, inputs={"val": 2}, input_types={"val": "INTEGER"})
    assert r1.status == "success"
    assert r1.outputs["flag"] == 20

    # 2. No condition matches (val = 99 -> flag remains 0)
    r2 = run_pipeline(code, inputs={"val": 99}, input_types={"val": "INTEGER"})
    assert r2.status == "success"
    assert r2.outputs["flag"] == 0


def test_execution_nested_else_if():
    """Test 33: Execution of nested ELSE IF statements."""
    code = """
    RULE NestedElif:
        category = "Unknown"
        IF level == 1 THEN
            category = "Tier 1"
        ELSE IF level == 2 THEN
            IF score >= 50 THEN
                category = "Tier 2 High"
            ELSE IF score >= 25 THEN
                category = "Tier 2 Medium"
            ELSE
                category = "Tier 2 Low"
            END
        ELSE
            category = "Other"
        END
    END
    """
    res = run_pipeline(
        code,
        inputs={"level": 2, "score": 30},
        input_types={"level": "INTEGER", "score": "INTEGER"},
    )
    assert res.status == "success"
    assert res.outputs["category"] == "Tier 2 Medium"


def test_execution_else_if_optimized_unoptimized_equivalence():
    """Test 34: Equivalence between optimized and unoptimized execution of ELSE IF."""
    code = """
    RULE EquivTest:
        base = 100
        IF score >= 90 THEN
            bonus = 50 + 10 * 2
            total = base + bonus
        ELSE IF score >= 70 THEN
            bonus = 20 + 5 * 2
            total = base + bonus
        ELSE
            bonus = 0
            total = base
        END
    END
    """
    for sc in [95, 80, 50]:
        res_opt = run_pipeline(code, inputs={"score": sc}, input_types={"score": "INTEGER"}, optimize=True)
        res_unopt = run_pipeline(code, inputs={"score": sc}, input_types={"score": "INTEGER"}, optimize=False)
        assert res_opt.status == "success"
        assert res_unopt.status == "success"
        assert res_opt.outputs == res_unopt.outputs


def test_execution_grade_evaluation_example_file():
    """Test 35: Validate examples/grade_evaluation.rf for marks 95, 82, 65, 40."""
    path = Path(__file__).parent.parent / "examples" / "grade_evaluation.rf"
    code = path.read_text(encoding="utf-8")

    expected_grades = {
        95: "A",
        82: "B",
        65: "C",
        40: "F",
    }

    for marks_val, expected_grade in expected_grades.items():
        res = run_pipeline(
            code,
            inputs={"marks": marks_val},
            input_types={"marks": "INTEGER"},
        )
        assert res.status == "success"
        assert res.outputs["grade"] == expected_grade
        assert res.outputs["marks"] == marks_val


# -------------------------------------------------------------
# 6. Built-in Function Execution Tests (Phase 7.2)
# -------------------------------------------------------------

def test_execution_all_builtin_functions():
    """Test 36: Execute all five built-in functions with dynamic inputs."""
    code = """
    RULE BuiltinsExec:
        res_abs1 = ABS(val_neg)
        res_abs2 = ABS(val_dec_neg)
        res_min1 = MIN(a, b)
        res_min2 = MIN(a, dec_val)
        res_max1 = MAX(a, b)
        res_max2 = MAX(a, dec_val)
        res_round1 = ROUND(round_up)
        res_round2 = ROUND(round_down)
        res_len = LENGTH(text)
    END
    """
    inputs = {
        "val_neg": -50,
        "val_dec_neg": -12.5,
        "a": 10,
        "b": 20,
        "dec_val": 5.5,
        "round_up": 3.7,
        "round_down": 3.2,
        "text": "Antigravity",
    }
    input_types = {
        "val_neg": "INTEGER",
        "val_dec_neg": "DECIMAL",
        "a": "INTEGER",
        "b": "INTEGER",
        "dec_val": "DECIMAL",
        "round_up": "DECIMAL",
        "round_down": "DECIMAL",
        "text": "STRING",
    }

    for opt in [False, True]:
        res = run_pipeline(code, inputs=inputs, input_types=input_types, optimize=opt)
        assert res.status == "success"
        out = res.outputs
        assert out["res_abs1"] == 50
        assert out["res_abs2"] == 12.5
        assert out["res_min1"] == 10
        assert out["res_min2"] == 5.5
        assert out["res_max1"] == 20
        assert out["res_max2"] == 10.0
        assert out["res_round1"] == 4
        assert out["res_round2"] == 3
        assert out["res_len"] == 11


def test_execution_nested_builtins_with_expressions():
    """Test 37: Execute nested built-ins within arithmetic expressions."""
    code = """
    RULE NestedMath:
        res = ABS(MIN(x, y) - MAX(x, y)) * ROUND(factor + 0.1)
    END
    """
    inputs = {"x": 10, "y": 25, "factor": 2.4}
    input_types = {"x": "INTEGER", "y": "INTEGER", "factor": "DECIMAL"}

    res = run_pipeline(code, inputs=inputs, input_types=input_types)
    assert res.status == "success"
    # |10 - 25| * round(2.5) -> 15 * 2 (or 3, round(2.5) in Python is 2, round(2.51) is 3)
    # factor = 2.4 + 0.1 = 2.5. Note round(2.5) in Python 3 banker's rounding is 2.
    # 15 * 2 = 30
    assert res.outputs["res"] == 15 * round(2.4 + 0.1)


def test_execution_builtin_functions_example_file():
    """Test 38: Execute examples/builtin_functions.rf end-to-end."""
    path = Path(__file__).parent.parent / "examples" / "builtin_functions.rf"
    code = path.read_text(encoding="utf-8")

    inputs = {
        "score": 85,
        "tax_rate": 18.75,
        "student_name": "RuleFlow",
    }
    input_types = {
        "score": "INTEGER",
        "tax_rate": "DECIMAL",
        "student_name": "STRING",
    }

    res = run_pipeline(code, inputs=inputs, input_types=input_types, optimize=True)
    assert res.status == "success"
    out = res.outputs
    assert out["abs_val"] == 42
    assert out["min_val"] == 85
    assert out["max_val"] == 85
    assert out["rounded_rate"] == 19
    assert out["name_len"] == 8
    # combined: ABS(85 - 85) + ROUND(12.7) -> 0 + 13 = 13
    assert out["combined"] == 13


def test_execution_builtin_function_runtime_errors():
    """Test 39: Directly invoke interpreter with invalid types to verify runtime safeguards."""
    from ruleflow.ir.instructions import FunctionCallInstruction
    from ruleflow.execution.interpreter import TACInterpreter

    # ABS with invalid string type
    ir = [FunctionCallInstruction(target="t1", func_name="ABS", args=["bad_val"])]
    env = RuntimeEnvironment()
    env.set_input("bad_val", "not_a_number")
    interp = TACInterpreter(ir, environment=env)
    res = interp.execute()
    assert res.status == "failed"
    assert "Function ABS requires exactly 1 numeric argument" in res.error


# -------------------------------------------------------------
# 7. WHILE Loop Execution Tests (Phase 7.3)
# -------------------------------------------------------------

def test_execution_while_countdown_and_sum():
    """Test 40: Execute countdown and summation loop, validating final outputs."""
    code = """
    RULE Countdown:
        count = 5
        total = 0

        WHILE count > 0 DO
            total = total + count
            count = count - 1
        END

        result = total
    END
    """
    for opt in [False, True]:
        res = run_pipeline(code, optimize=opt)
        assert res.status == "success"
        assert res.outputs["count"] == 0
        assert res.outputs["total"] == 15
        assert res.outputs["result"] == 15


def test_execution_while_loop_with_if_else():
    """Test 41: Execute WHILE loop containing conditional branching."""
    code = """
    RULE WhileIfBranch:
        i = 1
        evens = 0
        odds = 0

        WHILE i <= 6 DO
            IF i % 2 == 0 THEN
                evens = evens + 1
            ELSE
                odds = odds + 1
            END
            i = i + 1
        END
    END
    """
    for opt in [False, True]:
        res = run_pipeline(code, optimize=opt)
        assert res.status == "success"
        assert res.outputs["i"] == 7
        assert res.outputs["evens"] == 3
        assert res.outputs["odds"] == 3


def test_execution_nested_while_loops():
    """Test 42: Execute nested WHILE loops (multiplication accumulator)."""
    code = """
    RULE NestedWhile:
        i = 1
        product = 1

        WHILE i <= 3 DO
            j = 1
            WHILE j <= 2 DO
                product = product * 2
                j = j + 1
            END
            i = i + 1
        END
    END
    """
    for opt in [False, True]:
        res = run_pipeline(code, optimize=opt)
        assert res.status == "success"
        # Total inner iterations: 3 * 2 = 6, 2^6 = 64
        assert res.outputs["product"] == 64
        assert res.outputs["i"] == 4


def test_execution_multiple_sequential_while_loops():
    """Test 43: Execute multiple sequential WHILE loops."""
    code = """
    RULE SequentialWhile:
        a = 3
        sum_a = 0
        WHILE a > 0 DO
            sum_a = sum_a + a
            a = a - 1
        END

        b = 4
        sum_b = 0
        WHILE b > 0 DO
            sum_b = sum_b + b
            b = b - 1
        END

        combined = sum_a + sum_b
    END
    """
    for opt in [False, True]:
        res = run_pipeline(code, optimize=opt)
        assert res.status == "success"
        assert res.outputs["sum_a"] == 6
        assert res.outputs["sum_b"] == 10
        assert res.outputs["combined"] == 16


def test_execution_while_with_builtins():
    """Test 44: Execute WHILE loop using built-in functions in condition and body."""
    code = """
    RULE WhileBuiltins:
        val = -5
        steps = 0

        WHILE ABS(val) > 0 DO
            val = val + 1
            steps = steps + 1
        END
    END
    """
    for opt in [False, True]:
        res = run_pipeline(code, optimize=opt)
        assert res.status == "success"
        assert res.outputs["val"] == 0
        assert res.outputs["steps"] == 5


def test_execution_infinite_while_loop_step_limit():
    """Test 45: Infinite WHILE loop safely aborts via maximum step limit protection."""
    code = """
    RULE InfiniteLoop:
        x = 1
        WHILE x > 0 DO
            x = x + 1
        END
    END
    """
    res = run_pipeline(code, max_steps=100)
    assert res.status == "failed"
    assert "Execution step limit exceeded" in res.error


def test_execution_while_loop_example_file():
    """Test 46: Execute examples/while_loop.rf end-to-end."""
    path = Path(__file__).parent.parent / "examples" / "while_loop.rf"
    code = path.read_text(encoding="utf-8")

    for opt in [False, True]:
        res = run_pipeline(code, optimize=opt)
        assert res.status == "success"
        assert res.outputs["count"] == 0
        assert res.outputs["total"] == 15
        assert res.outputs["result"] == 15


