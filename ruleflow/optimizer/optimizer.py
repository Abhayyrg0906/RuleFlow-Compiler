"""Optimization module for RuleFlow Intermediate Representation.

Implements machine-independent optimization passes:
- Constant Propagation (with conservative control-flow boundary safety)
- Constant Folding (safe compile-time evaluation of arithmetic, comparisons, and logic)
- Dead Code Elimination (removal of unused pure temporary variables)
"""

import copy
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ruleflow.ir.instructions import (
    Instruction,
    Constant,
    AssignInstruction,
    BinaryOpInstruction,
    UnaryOpInstruction,
    LabelInstruction,
    JumpInstruction,
    JumpIfFalseInstruction,
    JumpIfTrueInstruction,
    RuleBoundaryInstruction,
    FunctionCallInstruction,
    FunctionBoundaryInstruction,
    ReturnInstruction,
)


class Optimizer:
    """Performs iterative optimization on Three-Address Code (TAC) instructions."""

    def __init__(self, ir_instructions: Optional[List[Instruction]] = None):
        self.ir_instructions: List[Instruction] = list(ir_instructions) if ir_instructions else []
        self.transformations: List[str] = []

    def get_log(self) -> List[str]:
        """Return human-readable log of applied optimization transformations."""
        return list(self.transformations)

    def optimize(self, ir_instructions: Optional[List[Instruction]] = None) -> List[Instruction]:
        """Apply constant propagation, constant folding, and dead code elimination.

        Returns:
            A new list of optimized instructions without mutating the input list.
        """
        source_ir = ir_instructions if ir_instructions is not None else self.ir_instructions
        current_ir = copy.deepcopy(source_ir)
        self.transformations = []

        max_iterations = 10
        for _ in range(max_iterations):
            changed = False

            # Pass 1: Constant Propagation
            current_ir, prop_changed = self._pass_constant_propagation(current_ir)
            if prop_changed:
                changed = True

            # Pass 2: Constant Folding
            current_ir, fold_changed = self._pass_constant_folding(current_ir)
            if fold_changed:
                changed = True

            # Pass 3: Dead Code Elimination (Temporaries)
            current_ir, dce_changed = self._pass_dead_code_elimination(current_ir)
            if dce_changed:
                changed = True

            if not changed:
                break

        return current_ir

    # -------------------------------------------------------------
    # Pass 1: Constant Propagation
    # -------------------------------------------------------------

    def _pass_constant_propagation(
        self, instructions: List[Instruction]
    ) -> Tuple[List[Instruction], bool]:
        """Propagate known constant values into variable usages within straight-line blocks."""
        new_instructions: List[Instruction] = []
        known_constants: Dict[str, Constant] = {}
        changed = False

        for inst in instructions:
            # Conservative control-flow boundary safety:
            # Clear known constants at labels, jumps, boundaries, and returns
            if isinstance(
                inst,
                (
                    LabelInstruction,
                    JumpInstruction,
                    JumpIfFalseInstruction,
                    JumpIfTrueInstruction,
                    RuleBoundaryInstruction,
                    FunctionBoundaryInstruction,
                    ReturnInstruction,
                ),
            ):
                # Before clearing on conditional jump, propagate condition if known
                if isinstance(inst, (JumpIfFalseInstruction, JumpIfTrueInstruction)):
                    cond = inst.condition
                    if isinstance(cond, str) and cond in known_constants:
                        new_cond = known_constants[cond]
                        if isinstance(inst, JumpIfFalseInstruction):
                            new_instructions.append(
                                JumpIfFalseInstruction(new_cond, inst.target_label)
                            )
                        else:
                            new_instructions.append(
                                JumpIfTrueInstruction(new_cond, inst.target_label)
                            )
                        self.transformations.append(
                            f"Propagated constant: {cond} = {new_cond} into jump condition"
                        )
                        changed = True
                    else:
                        new_instructions.append(inst)
                elif isinstance(inst, ReturnInstruction):
                    val = inst.value
                    if isinstance(val, str) and val in known_constants:
                        new_val = known_constants[val]
                        new_instructions.append(ReturnInstruction(value=new_val))
                        self.transformations.append(
                            f"Propagated constant into return: {val} = {new_val}"
                        )
                        changed = True
                    else:
                        new_instructions.append(inst)
                else:
                    new_instructions.append(inst)

                known_constants.clear()
                continue

            if isinstance(inst, AssignInstruction):
                src = inst.source
                if isinstance(src, str) and src in known_constants:
                    new_src = known_constants[src]
                    new_instructions.append(AssignInstruction(inst.target, new_src))
                    known_constants[inst.target] = new_src
                    self.transformations.append(
                        f"Propagated constant: {src} = {new_src} into {inst.target}"
                    )
                    changed = True
                else:
                    new_instructions.append(inst)
                    if isinstance(src, Constant):
                        known_constants[inst.target] = src
                    else:
                        known_constants.pop(inst.target, None)
                continue

            if isinstance(inst, BinaryOpInstruction):
                left = inst.left
                right = inst.right
                new_left = known_constants.get(left, left) if isinstance(left, str) else left
                new_right = (
                    known_constants.get(right, right) if isinstance(right, str) else right
                )

                if new_left != left or new_right != right:
                    new_instructions.append(
                        BinaryOpInstruction(inst.target, inst.op, new_left, new_right)
                    )
                    self.transformations.append(
                        f"Propagated operands into: {inst.target} = {new_left} {inst.op} {new_right}"
                    )
                    changed = True
                else:
                    new_instructions.append(inst)

                known_constants.pop(inst.target, None)
                continue

            if isinstance(inst, UnaryOpInstruction):
                operand = inst.operand
                new_operand = (
                    known_constants.get(operand, operand)
                    if isinstance(operand, str)
                    else operand
                )

                if new_operand != operand:
                    new_instructions.append(
                        UnaryOpInstruction(inst.target, inst.op, new_operand)
                    )
                    self.transformations.append(
                        f"Propagated operand into: {inst.target} = {inst.op} {new_operand}"
                    )
                    changed = True
                else:
                    new_instructions.append(inst)

                known_constants.pop(inst.target, None)
                continue

            if isinstance(inst, FunctionCallInstruction):
                new_args = [
                    known_constants.get(arg, arg) if isinstance(arg, str) else arg
                    for arg in inst.args
                ]
                if new_args != inst.args:
                    new_instructions.append(
                        FunctionCallInstruction(inst.target, inst.func_name, new_args)
                    )
                    self.transformations.append(
                        f"Propagated operands into: {inst.target} = {inst.func_name}({', '.join(str(a) for a in new_args)})"
                    )
                    changed = True
                else:
                    new_instructions.append(inst)

                known_constants.pop(inst.target, None)
                continue

            new_instructions.append(inst)

        return new_instructions, changed

    # -------------------------------------------------------------
    # Pass 2: Constant Folding
    # -------------------------------------------------------------

    def _pass_constant_folding(
        self, instructions: List[Instruction]
    ) -> Tuple[List[Instruction], bool]:
        """Statically evaluate operations whose operands are compile-time constants."""
        new_instructions: List[Instruction] = []
        changed = False

        for inst in instructions:
            if isinstance(inst, BinaryOpInstruction):
                if isinstance(inst.left, Constant) and isinstance(inst.right, Constant):
                    val_left = inst.left.value
                    val_right = inst.right.value
                    op = inst.op

                    folded_val = self._evaluate_binary_op(op, val_left, val_right)
                    if folded_val is not None:
                        new_instructions.append(
                            AssignInstruction(inst.target, Constant(folded_val))
                        )
                        self.transformations.append(
                            f"Constant folded: {val_left} {op} {val_right} -> {folded_val} ({inst.target})"
                        )
                        changed = True
                        continue

            elif isinstance(inst, UnaryOpInstruction):
                if isinstance(inst.operand, Constant):
                    val = inst.operand.value
                    op = inst.op

                    folded_val = self._evaluate_unary_op(op, val)
                    if folded_val is not None:
                        new_instructions.append(
                            AssignInstruction(inst.target, Constant(folded_val))
                        )
                        self.transformations.append(
                            f"Constant folded: {op} {val} -> {folded_val} ({inst.target})"
                        )
                        changed = True
                        continue

            elif isinstance(inst, FunctionCallInstruction):
                # Only fold pure built-in functions
                if inst.func_name.upper() in ("ABS", "MIN", "MAX", "ROUND", "LENGTH"):
                    if all(isinstance(arg, Constant) for arg in inst.args):
                        arg_values = [arg.value for arg in inst.args]
                        folded_val = self._evaluate_function_call(inst.func_name, arg_values)
                        if folded_val is not None:
                            new_instructions.append(
                                AssignInstruction(inst.target, Constant(folded_val))
                            )
                            self.transformations.append(
                                f"Constant folded: {inst.func_name}({', '.join(str(v) for v in arg_values)}) -> {folded_val} ({inst.target})"
                            )
                            changed = True
                            continue

            new_instructions.append(inst)

        return new_instructions, changed

    def _evaluate_binary_op(self, op: str, left: Any, right: Any) -> Optional[Any]:
        """Safely evaluate a binary operation on constant literal values."""
        # Arithmetic
        if op in ("+", "-", "*", "/", "%"):
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                return None
            if isinstance(left, bool) or isinstance(right, bool):
                return None

            try:
                if op == "+":
                    return left + right
                if op == "-":
                    return left - right
                if op == "*":
                    return left * right
                if op == "/":
                    if right == 0:
                        return None  # Do not crash on division by zero
                    return float(left) / float(right)
                if op == "%":
                    if right == 0:
                        return None  # Do not crash on modulo by zero
                    return left % right
            except Exception:
                return None

        # Relational comparisons
        if op in ("<", "<=", ">", ">="):
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                return None
            if isinstance(left, bool) or isinstance(right, bool):
                return None

            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            if op == ">=":
                return left >= right

        # Equality
        if op in ("==", "!="):
            # Safe equality comparison between compatible types
            # Do not equate booleans with numbers or strings with numbers
            if isinstance(left, bool) != isinstance(right, bool):
                return None
            if isinstance(left, str) != isinstance(right, str):
                return None
            try:
                if op == "==":
                    return left == right
                if op == "!=":
                    return left != right
            except Exception:
                return None

        # Boolean operations
        if op in ("AND", "OR"):
            if isinstance(left, bool) and isinstance(right, bool):
                if op == "AND":
                    return bool(left and right)
                if op == "OR":
                    return bool(left or right)

        return None

    def _evaluate_unary_op(self, op: str, val: Any) -> Optional[Any]:
        """Safely evaluate a unary operation on a constant literal value."""
        if op == "-":
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return -val
        if op == "+":
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return +val
        if op == "NOT":
            if isinstance(val, bool):
                return not val
        return None

    def _evaluate_function_call(self, func_name: str, args: List[Any]) -> Optional[Any]:
        """Safely evaluate a built-in function call on constant literal values."""
        fn = func_name.upper()
        if fn == "ABS":
            if len(args) == 1 and isinstance(args[0], (int, float)) and not isinstance(args[0], bool):
                res = abs(args[0])
                return float(res) if isinstance(args[0], float) else int(res)
        elif fn == "MIN":
            if len(args) == 2 and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in args):
                res = min(args[0], args[1])
                return float(res) if any(isinstance(a, float) for a in args) else int(res)
        elif fn == "MAX":
            if len(args) == 2 and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in args):
                res = max(args[0], args[1])
                return float(res) if any(isinstance(a, float) for a in args) else int(res)
        elif fn == "ROUND":
            if len(args) == 1 and isinstance(args[0], (int, float)) and not isinstance(args[0], bool):
                return int(round(args[0]))
        elif fn == "LENGTH":
            if len(args) == 1 and isinstance(args[0], str):
                return len(args[0])
        return None

    # -------------------------------------------------------------
    # Pass 3: Dead Code Elimination
    # -------------------------------------------------------------

    def _pass_dead_code_elimination(
        self, instructions: List[Instruction]
    ) -> Tuple[List[Instruction], bool]:
        """Remove unused temporary variable assignments that have no observable side effects."""
        used_vars: Set[str] = set()

        for inst in instructions:
            if isinstance(inst, AssignInstruction):
                if isinstance(inst.source, str):
                    used_vars.add(inst.source)
            elif isinstance(inst, BinaryOpInstruction):
                if isinstance(inst.left, str):
                    used_vars.add(inst.left)
                if isinstance(inst.right, str):
                    used_vars.add(inst.right)
            elif isinstance(inst, UnaryOpInstruction):
                if isinstance(inst.operand, str):
                    used_vars.add(inst.operand)
            elif isinstance(inst, (JumpIfFalseInstruction, JumpIfTrueInstruction)):
                if isinstance(inst.condition, str):
                    used_vars.add(inst.condition)
            elif isinstance(inst, FunctionCallInstruction):
                for arg in inst.args:
                    if isinstance(arg, str):
                        used_vars.add(arg)
            elif isinstance(inst, ReturnInstruction):
                if isinstance(inst.value, str):
                    used_vars.add(inst.value)

        new_instructions: List[Instruction] = []
        changed = False

        for inst in instructions:
            # Preserve user-defined function calls (do not eliminate even if target unused)
            if isinstance(inst, FunctionCallInstruction):
                if inst.func_name.upper() not in ("ABS", "MIN", "MAX", "ROUND", "LENGTH"):
                    new_instructions.append(inst)
                    continue

            # Check if this instruction defines an unused temporary variable (e.g. t1, t2)
            if isinstance(inst, (AssignInstruction, BinaryOpInstruction, UnaryOpInstruction, FunctionCallInstruction)):
                target = inst.target
                if self._is_temporary(target) and target not in used_vars:
                    # Do not remove division/modulo by zero (potentially unsafe operation)
                    if isinstance(inst, BinaryOpInstruction) and inst.op in ("/", "%"):
                        if isinstance(inst.right, Constant) and inst.right.value in (0, 0.0):
                            new_instructions.append(inst)
                            continue
                    self.transformations.append(
                        f"Removed unused temporary computation: {inst}"
                    )
                    changed = True
                    continue

            new_instructions.append(inst)

        return new_instructions, changed

    @staticmethod
    def _is_temporary(name: str) -> bool:
        """Check if a variable name matches compiler-generated temporary convention (t1, t2, ...)."""
        return bool(re.match(r"^t\d+$", name))


# Public API alias
IROptimizer = Optimizer
