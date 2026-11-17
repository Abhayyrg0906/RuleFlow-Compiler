"""Focused correctness audit tests for RuleFlow Compiler Module 4."""

from ruleflow.lexer import Lexer
from ruleflow.parser import Parser
from ruleflow.optimizer import Optimizer
from ruleflow.ir import (
    IRGenerator,
    Constant,
    AssignInstruction,
    BinaryOpInstruction,
    LabelInstruction,
    JumpInstruction,
    JumpIfFalseInstruction,
    JumpIfTrueInstruction,
)


def compile_to_ir(code: str):
    """Helper to produce raw and optimized IR from source code."""
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    raw_ir = IRGenerator(ast).generate()
    optimizer = Optimizer(raw_ir)
    opt_ir = optimizer.optimize()
    return raw_ir, opt_ir, optimizer


# -------------------------------------------------------------
# 1 & 2. Constant Propagation Around Branches & Isolation
# -------------------------------------------------------------

def test_audit_no_constant_leak_after_if_else():
    """Audit 1 & 2: Ensure branch-specific assignments do NOT leak constants after IF/ELSE."""
    code = """
    RULE AuditBranchLeak:
        x = 10
        IF cond THEN
            x = 20
        ELSE
            x = 30
        END
        post = x + 1
    END
    """
    _, opt_ir, _ = compile_to_ir(code)

    # In optimized IR, after LABEL L_end, post = x + 1 must NOT be folded to 21 or 31
    post_assigns = [
        inst for inst in opt_ir
        if isinstance(inst, (AssignInstruction, BinaryOpInstruction)) and inst.target == "post"
    ]
    assert len(post_assigns) >= 1
    # post must depend on variable x (or temporary of x), not a folded constant 21 or 31
    for inst in post_assigns:
        if isinstance(inst, AssignInstruction):
            assert inst.source != Constant(21) and inst.source != Constant(31)


def test_audit_nested_if_branch_isolation():
    """Audit 1: Constant propagation inside nested IF must not leak into outer code."""
    code = """
    RULE NestedIsolation:
        a = 5
        IF c1 THEN
            IF c2 THEN
                a = 99
            END
        END
        out = a + 1
    END
    """
    _, opt_ir, _ = compile_to_ir(code)
    out_assigns = [
        inst for inst in opt_ir
        if isinstance(inst, (AssignInstruction, BinaryOpInstruction)) and inst.target == "out"
    ]
    assert len(out_assigns) >= 1
    for inst in out_assigns:
        if isinstance(inst, AssignInstruction):
            assert inst.source != Constant(100)


# -------------------------------------------------------------
# 3. Short-Circuit Evaluation Semantics
# -------------------------------------------------------------

def test_audit_short_circuit_and_or_structure():
    """Audit 3: AND and OR generate proper short-circuit jumps skipping the second operand."""
    code = """
    RULE ShortCircuitAudit:
        r_and = a AND b
        r_or = c OR d
    END
    """
    raw_ir, opt_ir, _ = compile_to_ir(code)

    # AND must have: JumpIfFalse skipping b, landing on false label
    and_jumps = [i for i in raw_ir if isinstance(i, JumpIfFalseInstruction)]
    and_labels = [i for i in raw_ir if isinstance(i, LabelInstruction) and "false" in i.label]
    assert len(and_jumps) >= 1
    assert len(and_labels) >= 1

    # OR must have: JumpIfTrue skipping d, landing on true label
    or_jumps = [i for i in raw_ir if isinstance(i, JumpIfTrueInstruction)]
    or_labels = [i for i in raw_ir if isinstance(i, LabelInstruction) and "true" in i.label]
    assert len(or_jumps) >= 1
    assert len(or_labels) >= 1


# -------------------------------------------------------------
# 4. Jump Targets Must Reference Existing Labels
# -------------------------------------------------------------

def test_audit_all_jumps_reference_existing_labels():
    """Audit 4: Every JumpInstruction, JumpIfFalse, and JumpIfTrue references an existing label."""
    code = """
    RULE ComplexJumps:
        IF (gpa >= 3.5 AND attendance >= 75) OR status == "VIP" THEN
            IF score > 90 THEN
                honor = 1
            ELSE
                honor = 0
            END
        ELSE
            honor = -1
        END
    END
    """
    raw_ir, opt_ir, _ = compile_to_ir(code)

    for ir_list in (raw_ir, opt_ir):
        declared_labels = {i.label for i in ir_list if isinstance(i, LabelInstruction)}

        for inst in ir_list:
            if isinstance(inst, JumpInstruction):
                assert inst.target_label in declared_labels, f"Missing label: {inst.target_label}"
            elif isinstance(inst, (JumpIfFalseInstruction, JumpIfTrueInstruction)):
                assert inst.target_label in declared_labels, f"Missing label: {inst.target_label}"


# -------------------------------------------------------------
# 5. Label Uniqueness Across Multiple Rules
# -------------------------------------------------------------

def test_audit_label_uniqueness_across_multiple_rules():
    """Audit 5: Label names remain globally unique across multiple rules in the same program."""
    code = """
    RULE RuleA:
        IF x > 0 THEN
            a = 1
        ELSE
            a = 2
        END
    END

    RULE RuleB:
        IF y > 0 THEN
            b = 1
        ELSE
            b = 2
        END
    END

    RULE RuleC:
        flag = p AND q
    END
    """
    raw_ir, _, _ = compile_to_ir(code)
    labels = [i.label for i in raw_ir if isinstance(i, LabelInstruction)]

    # Assert no duplicate labels exist
    assert len(labels) == len(set(labels)), f"Duplicate labels found: {labels}"
    assert len(labels) >= 6


# -------------------------------------------------------------
# 6. Named Variables Preservation
# -------------------------------------------------------------

def test_audit_all_named_variables_preserved():
    """Audit 6: Optimized IR preserves all named variable assignments even if unused."""
    code = """
    RULE UnusedNamed:
        assigned_only = 100
        never_read_str = "audit"
        never_read_calc = 10 + 20
        result = 42
    END
    """
    _, opt_ir, _ = compile_to_ir(code)
    named_targets = {
        inst.target for inst in opt_ir
        if isinstance(inst, AssignInstruction) and not inst.target.startswith("t")
    }

    assert "assigned_only" in named_targets
    assert "never_read_str" in named_targets
    assert "never_read_calc" in named_targets
    assert "result" in named_targets


# -------------------------------------------------------------
# 7. Immutability of Original IR
# -------------------------------------------------------------

def test_audit_original_ir_immutability():
    """Audit 7: Optimization leaves the original raw IR list and instruction objects untouched."""
    code = """
    RULE ImmutabilityTest:
        result = 10 + 20 * 2
    END
    """
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    raw_ir = IRGenerator(ast).generate()

    # Capture string representations before optimization
    raw_snapshot = [str(inst) for inst in raw_ir]

    optimizer = Optimizer(raw_ir)
    opt_ir = optimizer.optimize()

    # Raw IR should be completely unchanged
    assert [str(inst) for inst in raw_ir] == raw_snapshot
    assert raw_ir is not opt_ir
    assert len(raw_ir) > len(opt_ir)


# -------------------------------------------------------------
# 8. Safe Handling of String, Boolean, Integer, and Decimal Constants
# -------------------------------------------------------------

def test_audit_constant_types_strict_separation():
    """Audit 8: Strict type safety for Constant: booleans != numbers, floats preserved."""
    # Boolean vs integer
    assert Constant(True) != Constant(1)
    assert Constant(False) != Constant(0)
    assert Constant(True) == Constant(True)
    assert Constant(False) == Constant(False)

    # Float vs integer representation
    assert Constant(3.5).value == 3.5
    assert Constant(42).value == 42
    assert Constant("test").value == "test"

    # Optimizer does not equate True with 1
    raw_ir = [
        BinaryOpInstruction("t1", "==", Constant(True), Constant(1)),
        AssignInstruction("res", "t1"),
    ]
    opt_ir = Optimizer(raw_ir).optimize()
    # Should not fold True == 1 into True
    assign = [i for i in opt_ir if isinstance(i, AssignInstruction) and i.target == "res"][0]
    assert assign.source != Constant(True)


def test_audit_unsafe_division_by_zero_temporary_preserved():
    """Audit: Unsafe operations (e.g. division by literal zero) are not silently eliminated by DCE."""
    raw_ir = [
        AssignInstruction("x", Constant(10)),
        BinaryOpInstruction("t1", "/", "x", Constant(0)),  # Unsafe operation
    ]
    opt_ir = Optimizer(raw_ir).optimize()
    # The unsafe binary op instruction t1 = x / 0 must be preserved, not removed
    ops = [i for i in opt_ir if isinstance(i, BinaryOpInstruction)]
    assert len(ops) == 1
    assert ops[0].op == "/"
