"""Unit tests for RuleFlow Intermediate Code Generation (TAC)."""

from ruleflow.lexer import Lexer
from ruleflow.parser import Parser
from ruleflow.ir import (
    IRGenerator,
    AssignInstruction,
    BinaryOpInstruction,
    UnaryOpInstruction,
    LabelInstruction,
    JumpInstruction,
    JumpIfFalseInstruction,
    JumpIfTrueInstruction,
    RuleBoundaryInstruction,
    Constant,
)


def generate_ir(code: str):
    """Helper function to tokenize, parse, and generate IR instructions."""
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    generator = IRGenerator(ast)
    return generator.generate()


def test_simple_assignment():
    """Test 1: Simple assignment generates AssignInstruction."""
    code = """
    RULE SimpleAssign:
        x = 42
        msg = "Hello"
    END
    """
    ir = generate_ir(code)
    # Check instructions inside boundaries
    assigns = [inst for inst in ir if isinstance(inst, AssignInstruction)]
    assert len(assigns) == 2
    assert assigns[0].target == "x"
    assert assigns[0].source == Constant(42)
    assert assigns[1].target == "msg"
    assert assigns[1].source == Constant("Hello")


def test_arithmetic_operator_precedence():
    """Test 2: Arithmetic operator precedence: result = 10 + 20 * 2."""
    code = """
    RULE Calculation:
        result = 10 + 20 * 2
    END
    """
    ir = generate_ir(code)
    # Expected:
    # t1 = 20 * 2
    # t2 = 10 + t1
    # result = t2
    bin_ops = [inst for inst in ir if isinstance(inst, BinaryOpInstruction)]
    assert len(bin_ops) == 2
    assert bin_ops[0].target == "t1"
    assert bin_ops[0].op == "*"
    assert bin_ops[0].left == Constant(20)
    assert bin_ops[0].right == Constant(2)

    assert bin_ops[1].target == "t2"
    assert bin_ops[1].op == "+"
    assert bin_ops[1].left == Constant(10)
    assert bin_ops[1].right == "t1"

    assign = [inst for inst in ir if isinstance(inst, AssignInstruction)][0]
    assert assign.target == "result"
    assert assign.source == "t2"


def test_parenthesized_expressions():
    """Test 3: Parentheses override precedence: (10 + 20) * 2."""
    code = """
    RULE Grouped:
        result = (10 + 20) * 2
    END
    """
    ir = generate_ir(code)
    bin_ops = [inst for inst in ir if isinstance(inst, BinaryOpInstruction)]
    assert len(bin_ops) == 2
    # First evaluates addition inside parentheses
    assert bin_ops[0].op == "+"
    assert bin_ops[0].left == Constant(10)
    assert bin_ops[0].right == Constant(20)

    # Then multiplication
    assert bin_ops[1].op == "*"
    assert bin_ops[1].left == "t1"
    assert bin_ops[1].right == Constant(2)


def test_unary_expressions():
    """Test 4: Unary expressions: negative and NOT."""
    code = """
    RULE Unary:
        a = -x
        b = NOT flag
    END
    """
    ir = generate_ir(code)
    unary_ops = [inst for inst in ir if isinstance(inst, UnaryOpInstruction)]
    assert len(unary_ops) == 2
    assert unary_ops[0].op == "-"
    assert unary_ops[0].operand == "x"
    assert unary_ops[1].op == "NOT"
    assert unary_ops[1].operand == "flag"


def test_relational_expressions():
    """Test 5: Relational expressions: >= and <."""
    code = """
    RULE Compare:
        is_ok = gpa >= 3.5
    END
    """
    ir = generate_ir(code)
    bin_ops = [inst for inst in ir if isinstance(inst, BinaryOpInstruction)]
    assert len(bin_ops) == 1
    assert bin_ops[0].op == ">="
    assert bin_ops[0].left == "gpa"
    assert bin_ops[0].right == Constant(3.5)


def test_logical_expressions_short_circuit():
    """Test 6: Short-circuit control-flow code generation for AND/OR."""
    code = """
    RULE Logic:
        res = a AND b
    END
    """
    ir = generate_ir(code)
    # Must contain conditional jumps and labels for short-circuiting
    jumps_if_false = [inst for inst in ir if isinstance(inst, JumpIfFalseInstruction)]
    labels = [inst for inst in ir if isinstance(inst, LabelInstruction)]
    gotos = [inst for inst in ir if isinstance(inst, JumpInstruction)]

    assert len(jumps_if_false) >= 1
    assert len(labels) >= 2
    assert len(gotos) >= 1


def test_if_without_else():
    """Test 7: Conditional IF without ELSE branch."""
    code = """
    RULE SimpleIf:
        IF score > 50 THEN
            passed = 1
        END
    END
    """
    ir = generate_ir(code)
    jumps_if_false = [inst for inst in ir if isinstance(inst, JumpIfFalseInstruction)]
    labels = [inst for inst in ir if isinstance(inst, LabelInstruction)]
    gotos = [inst for inst in ir if isinstance(inst, JumpInstruction)]

    assert len(jumps_if_false) == 1
    assert len(labels) == 1
    assert len(gotos) == 0
    # Jump target must match the label
    assert jumps_if_false[0].target_label == labels[0].label


def test_if_with_else():
    """Test 8: Conditional IF with ELSE branch."""
    code = """
    RULE IfElse:
        IF gpa >= 3.5 THEN
            status = "Eligible"
        ELSE
            status = "Not Eligible"
        END
    END
    """
    ir = generate_ir(code)
    jumps_if_false = [inst for inst in ir if isinstance(inst, JumpIfFalseInstruction)]
    labels = [inst for inst in ir if isinstance(inst, LabelInstruction)]
    gotos = [inst for inst in ir if isinstance(inst, JumpInstruction)]

    assert len(jumps_if_false) == 1
    assert len(labels) == 2  # L_else and L_end
    assert len(gotos) == 1   # GOTO L_end


def test_nested_if_statements():
    """Test 9: Nested IF statements generate unique labels and correct targets."""
    code = """
    RULE Nested:
        IF a == 1 THEN
            IF b == 2 THEN
                x = 10
            END
        END
    END
    """
    ir = generate_ir(code)
    labels = [inst.label for inst in ir if isinstance(inst, LabelInstruction)]
    # All labels must be unique
    assert len(labels) == len(set(labels))
    assert len(labels) >= 2


def test_multiple_rules_and_boundaries():
    """Test 10: Multiple rules with distinct boundaries and unique labels."""
    code = """
    RULE RuleOne:
        x = 1
    END

    RULE RuleTwo:
        y = 2
    END
    """
    ir = generate_ir(code)
    boundaries = [inst for inst in ir if isinstance(inst, RuleBoundaryInstruction)]
    assert len(boundaries) == 4
    assert boundaries[0].name == "RuleOne" and boundaries[0].is_start
    assert boundaries[1].name == "RuleOne" and not boundaries[1].is_start
    assert boundaries[2].name == "RuleTwo" and boundaries[2].is_start
    assert boundaries[3].name == "RuleTwo" and not boundaries[3].is_start


# -------------------------------------------------------------
# Tests 11-12: ELSE IF TAC Generation
# -------------------------------------------------------------

def test_ir_multiple_else_if_branches():
    """Test 11: TAC generation for chained ELSE IF statements with final ELSE."""
    code = """
    RULE GradeEval:
        IF marks >= 90 THEN
            grade = "A"
        ELSE IF marks >= 75 THEN
            grade = "B"
        ELSE
            grade = "C"
        END
    END
    """
    ir = generate_ir(code)
    jumps_if_false = [inst for inst in ir if isinstance(inst, JumpIfFalseInstruction)]
    gotos = [inst for inst in ir if isinstance(inst, JumpInstruction)]
    labels = [inst.label for inst in ir if isinstance(inst, LabelInstruction)]

    # Two condition checks: IF marks >= 90 and ELSE IF marks >= 75
    assert len(jumps_if_false) == 2
    # Two branches (THEN and ELIF) jump to end label
    assert len(gotos) == 2
    # Labels: L_elif, L_else, L_end
    assert len(labels) == 3
    # All labels must be unique
    assert len(labels) == len(set(labels))
    # Every jump target exists as a label
    for j in jumps_if_false:
        assert j.target_label in labels
    for g in gotos:
        assert g.target_label in labels


def test_ir_else_if_without_else():
    """Test 12: TAC generation for ELSE IF without a final ELSE branch."""
    code = """
    RULE NoElse:
        IF x == 1 THEN
            y = 10
        ELSE IF x == 2 THEN
            y = 20
        END
    END
    """
    ir = generate_ir(code)
    jumps_if_false = [inst for inst in ir if isinstance(inst, JumpIfFalseInstruction)]
    labels = [inst.label for inst in ir if isinstance(inst, LabelInstruction)]

    assert len(jumps_if_false) == 2
    # Labels: L_elif and L_end
    assert len(labels) == 2
    for j in jumps_if_false:
        assert j.target_label in labels


def test_ir_builtin_function_calls():
    """Test 13: TAC generation for built-in function calls."""
    from ruleflow.ir.instructions import FunctionCallInstruction

    code = """
    RULE BuiltinsIR:
        x = ABS(-5)
        m = MIN(x, 10)
        len = LENGTH("test")
    END
    """
    ir = generate_ir(code)
    fn_calls = [inst for inst in ir if isinstance(inst, FunctionCallInstruction)]
    assert len(fn_calls) == 3

    assert fn_calls[0].func_name == "ABS"
    assert fn_calls[1].func_name == "MIN"
    assert fn_calls[2].func_name == "LENGTH"

    # Check to_dict and str
    d = fn_calls[0].to_dict()
    assert d["type"] == "FunctionCallInstruction"
    assert d["op"] == "CALL ABS"
    assert "ABS" in str(fn_calls[0])


def test_ir_nested_function_calls():
    """Test 14: TAC generation for nested function calls."""
    from ruleflow.ir.instructions import FunctionCallInstruction

    code = """
    RULE NestedIR:
        res = ROUND(MIN(10.5, 20.0))
    END
    """
    ir = generate_ir(code)
    fn_calls = [inst for inst in ir if isinstance(inst, FunctionCallInstruction)]
    assert len(fn_calls) == 2
    # Inner call is MIN, outer is ROUND
    assert fn_calls[0].func_name == "MIN"
    assert fn_calls[1].func_name == "ROUND"
    assert fn_calls[1].args[0] == fn_calls[0].target

