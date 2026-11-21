"""Unit tests for RuleFlow IR Optimization (Constant Folding, Propagation, DCE)."""

from ruleflow.lexer import Lexer
from ruleflow.parser import Parser
from ruleflow.optimizer import Optimizer, IROptimizer
from ruleflow.ir import (
    IRGenerator,
    Constant,
    AssignInstruction,
    BinaryOpInstruction,
    LabelInstruction,
    JumpInstruction,
    JumpIfFalseInstruction,
)


def get_optimized_ir(code: str):
    """Helper to generate IR and run optimization."""
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    raw_ir = IRGenerator(ast).generate()
    optimizer = Optimizer(raw_ir)
    optimized_ir = optimizer.optimize()
    return raw_ir, optimized_ir, optimizer


def test_constant_folding_simple():
    """Test 11: Constant folding: 20 * 2 -> 40."""
    code = """
    RULE Calc:
        result = 20 * 2
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    assigns = [inst for inst in opt_ir if isinstance(inst, AssignInstruction) and inst.target == "result"]
    assert len(assigns) == 1
    assert assigns[0].source == Constant(40)


def test_multiple_constant_operations():
    """Test 12: Multiple constant operations chained together."""
    code = """
    RULE Chained:
        result = 10 + 20 * 2
    END
    """
    raw_ir, opt_ir, _ = get_optimized_ir(code)
    # Check that raw IR had 3 instructions (t1, t2, result)
    assert len([inst for inst in raw_ir if isinstance(inst, (AssignInstruction, BinaryOpInstruction))]) == 3

    # In optimized IR, result should be 50 directly, and unused temporaries removed
    assigns = [inst for inst in opt_ir if isinstance(inst, AssignInstruction) and inst.target == "result"]
    assert len(assigns) == 1
    assert assigns[0].source == Constant(50)


def test_constant_propagation():
    """Test 13: Constant propagation across sequential statements."""
    code = """
    RULE Propagate:
        x = 10
        y = x + 5
        result = y * 2
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    assigns = {
        inst.target: inst.source
        for inst in opt_ir
        if isinstance(inst, AssignInstruction) and not inst.target.startswith("t")
    }

    assert assigns["x"] == Constant(10)
    assert assigns["y"] == Constant(15)
    assert assigns["result"] == Constant(30)


def test_reassignment_invalidates_propagated_constants():
    """Test 14: Reassignment invalidates previously known constant value."""
    # When x is reassigned dynamically or with a new value
    code = """
    RULE Reassign:
        x = 10
        y = x + 5
        x = y + 2
        z = x + 1
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    assigns = {
        inst.target: inst.source
        for inst in opt_ir
        if isinstance(inst, AssignInstruction) and inst.target in ("x", "y", "z")
    }
    # y = 15, x = 17, z = 18
    assert assigns["y"] == Constant(15)
    assert assigns["x"] == Constant(17)
    assert assigns["z"] == Constant(18)


def test_constant_comparisons():
    """Test 15: Constant comparisons evaluated at compile time."""
    code = """
    RULE Compare:
        a = 10 > 5
        b = 20 <= 15
        c = 5 == 5
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    assigns = {
        inst.target: inst.source
        for inst in opt_ir
        if isinstance(inst, AssignInstruction) and inst.target in ("a", "b", "c")
    }
    assert assigns["a"] == Constant(True)
    assert assigns["b"] == Constant(False)
    assert assigns["c"] == Constant(True)


def test_boolean_constant_expressions():
    """Test 16: Boolean constant operations folded correctly."""
    # 1. Unary NOT on constant comparison: NOT (10 > 20) -> NOT False -> True
    code = """
    RULE BoolLogic:
        flag1 = NOT (10 > 20)
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    assigns = {
        inst.target: inst.source
        for inst in opt_ir
        if isinstance(inst, AssignInstruction) and inst.target == "flag1"
    }
    assert assigns["flag1"] == Constant(True)

    # 2. Binary boolean folding (AND / OR)
    raw_ir = [
        BinaryOpInstruction("t1", "AND", Constant(True), Constant(False)),
        BinaryOpInstruction("t2", "OR", Constant(False), Constant(True)),
        AssignInstruction("res_and", "t1"),
        AssignInstruction("res_or", "t2"),
    ]
    opt_ir = Optimizer(raw_ir).optimize()
    res_assigns = {
        inst.target: inst.source
        for inst in opt_ir
        if isinstance(inst, AssignInstruction) and inst.target in ("res_and", "res_or")
    }
    assert res_assigns["res_and"] == Constant(False)
    assert res_assigns["res_or"] == Constant(True)


def test_division_by_zero_does_not_crash_optimizer():
    """Test 17: Optimizer handles division by zero safely without crashing."""
    # Construct raw instructions containing division by zero directly
    raw_ir = [
        AssignInstruction("x", Constant(10)),
        BinaryOpInstruction("t1", "/", "x", Constant(0)),
        AssignInstruction("result", "t1"),
    ]
    optimizer = IROptimizer(raw_ir)
    opt_ir = optimizer.optimize()

    # Must return without throwing ZeroDivisionError
    assert len(opt_ir) > 0


def test_safe_removal_of_unused_temporaries():
    """Test 18: Unused compiler temporaries are safely removed."""
    raw_ir = [
        BinaryOpInstruction("t1", "+", Constant(1), Constant(2)),  # never used
        AssignInstruction("x", Constant(100)),
    ]
    optimizer = Optimizer(raw_ir)
    opt_ir = optimizer.optimize()

    targets = [inst.target for inst in opt_ir if hasattr(inst, "target")]
    assert "t1" not in targets
    assert "x" in targets


def test_named_variables_preserved():
    """Test 19: Named RuleFlow variables are never removed by DCE."""
    code = """
    RULE NamedVars:
        a = 10
        b = 20
        c = 30
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    targets = [inst.target for inst in opt_ir if isinstance(inst, AssignInstruction)]
    assert "a" in targets
    assert "b" in targets
    assert "c" in targets


def test_control_flow_labels_and_jumps_preserved():
    """Test 20: Control-flow labels and jumps remain intact after optimization."""
    code = """
    RULE IfBranch:
        IF score > 50 THEN
            status = "Pass"
        ELSE
            status = "Fail"
        END
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    labels = [inst for inst in opt_ir if isinstance(inst, LabelInstruction)]
    jumps_if_false = [inst for inst in opt_ir if isinstance(inst, JumpIfFalseInstruction)]
    gotos = [inst for inst in opt_ir if isinstance(inst, JumpInstruction)]

    assert len(labels) == 2
    assert len(jumps_if_false) == 1
    assert len(gotos) == 1


# -------------------------------------------------------------
# 5. Built-in Function Optimization Tests (Phase 7.2)
# -------------------------------------------------------------

def test_builtin_function_constant_folding():
    """Verify compile-time constant folding for all five built-in functions."""
    code = """
    RULE FoldBuiltins:
        a = ABS(-42)
        b = MIN(15, 30)
        c = MAX(15, 30)
        d = ROUND(12.6)
        e = LENGTH("RuleFlow")
    END
    """
    _, opt_ir, opt = get_optimized_ir(code)

    assigns = {
        inst.target: inst.source.value
        for inst in opt_ir
        if isinstance(inst, AssignInstruction) and isinstance(inst.source, Constant)
    }

    assert assigns["a"] == 42
    assert assigns["b"] == 15
    assert assigns["c"] == 30
    assert assigns["d"] == 13
    assert assigns["e"] == 8


def test_builtin_function_propagation_and_nested_folding():
    """Verify constant propagation into function arguments and nested folding."""
    code = """
    RULE NestedFolding:
        x = -25
        y = ABS(x)
        nested = ROUND(MIN(14.8, 20.2))
    END
    """
    _, opt_ir, opt = get_optimized_ir(code)

    assigns = {
        inst.target: inst.source.value
        for inst in opt_ir
        if isinstance(inst, AssignInstruction) and isinstance(inst.source, Constant)
    }

    assert assigns["x"] == -25
    assert assigns["y"] == 25
    assert assigns["nested"] == 15


# -------------------------------------------------------------
# 6. WHILE Loop Optimizer Tests (Phase 7.3)
# -------------------------------------------------------------

def test_while_loop_no_constant_leak_into_loop():
    """Verify that variables modified in a loop are not statically folded as initial constants."""
    code = """
    RULE LoopSafety:
        count = 5
        WHILE count > 0 DO
            count = count - 1
        END
        result = count
    END
    """
    _, opt_ir, opt = get_optimized_ir(code)

    # Verify loop condition still tests dynamic 'count', not folded constant
    binops = [inst for inst in opt_ir if isinstance(inst, BinaryOpInstruction)]
    cond_binop = [b for b in binops if b.op == ">"][0]
    assert cond_binop.left == "count"  # Not folded into Constant(5) > Constant(0)

    # Verify loop labels and jumps remain intact
    labels = [inst.label for inst in opt_ir if isinstance(inst, LabelInstruction)]
    gotos = [inst for inst in opt_ir if isinstance(inst, JumpInstruction)]
    jumps_if_false = [inst for inst in opt_ir if isinstance(inst, JumpIfFalseInstruction)]

    assert len(labels) == 2
    assert len(gotos) == 1
    assert len(jumps_if_false) == 1


def test_while_loop_labels_and_jumps_preserved():
    """Verify that loop labels, backward jumps, and exit jumps are fully preserved."""
    code = """
    RULE PreserveLoops:
        x = 0
        WHILE x < 10 DO
            x = x + 1
        END
    END
    """
    raw_ir, opt_ir, _ = get_optimized_ir(code)

    raw_labels = [inst.label for inst in raw_ir if isinstance(inst, LabelInstruction)]
    opt_labels = [inst.label for inst in opt_ir if isinstance(inst, LabelInstruction)]

    assert raw_labels == opt_labels


# -------------------------------------------------------------
# User-Defined Functions Optimization Tests (Phase 7.4)
# -------------------------------------------------------------

def test_optimizer_preserves_function_boundaries_and_returns():
    """Verify that FunctionBoundaryInstruction and ReturnInstruction are preserved."""
    from ruleflow.ir.instructions import FunctionBoundaryInstruction, ReturnInstruction

    code = """
    FUNCTION DoubleVal(x: INTEGER) RETURNS INTEGER:
        res = x * 2
        RETURN res
    END

    RULE CallRule:
        a = DoubleVal(5)
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)

    boundaries = [inst for inst in opt_ir if isinstance(inst, FunctionBoundaryInstruction)]
    assert len(boundaries) == 2
    assert boundaries[0].is_start is True
    assert boundaries[0].name == "DoubleVal"
    assert boundaries[1].is_start is False

    returns = [inst for inst in opt_ir if isinstance(inst, ReturnInstruction)]
    assert len(returns) == 1


def test_optimizer_does_not_eliminate_function_calls():
    """Verify that user-defined function calls are preserved during dead code elimination."""
    from ruleflow.ir.instructions import FunctionCallInstruction

    code = """
    FUNCTION SideEffect(x: INTEGER) RETURNS INTEGER:
        RETURN x + 1
    END

    RULE CallRule:
        unused = SideEffect(10)
        kept = 42
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    calls = [inst for inst in opt_ir if isinstance(inst, FunctionCallInstruction)]
    assert len(calls) == 1
    assert calls[0].func_name == "SideEffect"


def test_optimizer_constants_do_not_propagate_across_function_boundaries():
    """Verify that known constants do not propagate across function boundaries."""
    code = """
    FUNCTION Helper(a: INTEGER) RETURNS INTEGER:
        local_c = 10
        RETURN a + local_c
    END

    RULE Caller:
        local_c = 20
        res = Helper(5)
        out = local_c
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    # The output variable 'out' should equal 20, unaffected by Helper's internal local_c
    copy_insts = [inst for inst in opt_ir if hasattr(inst, "target") and inst.target == "out"]
    assert len(copy_insts) == 1
    assert getattr(copy_insts[0].source, "value", copy_insts[0].source) == 20


def test_optimizer_constant_folding_inside_function():
    """Verify that pure constant sub-expressions fold inside function bodies."""
    from ruleflow.ir.instructions import ReturnInstruction

    code = """
    FUNCTION Precomputed() RETURNS INTEGER:
        val = 10 + 20 * 2
        RETURN val
    END

    RULE Run:
        x = Precomputed()
    END
    """
    _, opt_ir, _ = get_optimized_ir(code)
    # 10 + 20 * 2 = 50 should fold
    ret = [inst for inst in opt_ir if isinstance(inst, ReturnInstruction)][0]
    assert getattr(ret.value, "value", ret.value) == 50



