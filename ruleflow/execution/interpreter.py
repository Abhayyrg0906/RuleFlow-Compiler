"""Direct Three-Address Code (TAC) interpreter for RuleFlow Compiler."""

from typing import Any, Dict, List, Optional, Tuple
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
from .runtime import RuntimeEnvironment
from .errors import ExecutionError


class ExecutionResult:
    """Encapsulates the final result, environment state, and trace of a program execution."""

    def __init__(
        self,
        status: str,
        outputs: Dict[str, Any],
        environment: Optional[Dict[str, Any]] = None,
        step_count: int = 0,
        trace: Optional[List[str]] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.status = status
        self.outputs = outputs
        self.environment = environment or {}
        self.step_count = step_count
        self.trace = trace or []
        self.error = error
        self.message = message

    @property
    def steps(self) -> int:
        """Alias for step_count to support .steps access."""
        return self.step_count

    @steps.setter
    def steps(self, value: int) -> None:
        self.step_count = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert execution result to a dictionary representation."""
        return {
            "status": self.status,
            "outputs": self.outputs,
            "output": self.outputs,  # Alias for backward compatibility
            "environment": self.environment,
            "step_count": self.step_count,
            "steps": self.step_count,
            "trace": self.trace,
            "error": self.error,
            "message": self.message,
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __repr__(self) -> str:
        return f"ExecutionResult(status={repr(self.status)}, outputs={repr(self.outputs)}, steps={self.step_count})"


class TACInterpreter:
    """Interprets and executes a linear sequence of Three-Address Code instructions directly."""

    def __init__(
        self,
        instructions: List[Instruction],
        environment: Optional[RuntimeEnvironment] = None,
        max_steps: int = 10000,
    ):
        self.instructions = list(instructions)
        self.env = environment if environment is not None else RuntimeEnvironment()
        self.max_steps = max_steps

    def resolve_operand(self, operand: Any) -> Any:
        """Resolve an operand into its concrete runtime value."""
        if isinstance(operand, Constant):
            return operand.value
        if isinstance(operand, str):
            return self.env.get(operand)
        return operand

    def execute(self) -> ExecutionResult:
        """Execute the instruction stream directly using a program counter and label table.

        Returns:
            ExecutionResult with final status, named outputs, environment, and trace.
        """
        # Step 1: Pre-index label positions and user-defined functions
        label_map: Dict[str, int] = {}
        function_map: Dict[str, Dict[str, Any]] = {}
        for idx, inst in enumerate(self.instructions):
            if isinstance(inst, LabelInstruction):
                label_map[inst.label] = idx
            elif isinstance(inst, FunctionBoundaryInstruction) and inst.is_start:
                entry_label = f"L_func_{inst.name}"
                function_map[inst.name] = {
                    "entry_label": entry_label,
                    "params": inst.params,
                }

        # Call frame stack: list of (return_pc, target_var, caller_env, func_name)
        call_stack: List[Tuple[int, str, RuntimeEnvironment, str]] = []

        pc = 0
        step = 0
        trace: List[str] = []

        try:
            while pc < len(self.instructions):
                step += 1
                if step > self.max_steps:
                    raise ExecutionError(
                        f"Execution step limit exceeded ({self.max_steps} steps). Potential infinite loop detected.",
                        step=step,
                    )

                inst = self.instructions[pc]

                # 1. Assignment
                if isinstance(inst, AssignInstruction):
                    val = self.resolve_operand(inst.source)
                    self.env.set(inst.target, val)
                    trace.append(f"Step {step:04d} | PC {pc:03d} | {inst.target} = {repr(val)}")
                    pc += 1

                # 2. Binary Operation
                elif isinstance(inst, BinaryOpInstruction):
                    left_val = self.resolve_operand(inst.left)
                    right_val = self.resolve_operand(inst.right)
                    res = self._execute_binary_op(inst.op, left_val, right_val, step, inst)
                    self.env.set(inst.target, res)
                    trace.append(
                        f"Step {step:04d} | PC {pc:03d} | {inst.target} = {repr(left_val)} {inst.op} {repr(right_val)} -> {repr(res)}"
                    )
                    pc += 1

                # 3. Unary Operation
                elif isinstance(inst, UnaryOpInstruction):
                    op_val = self.resolve_operand(inst.operand)
                    res = self._execute_unary_op(inst.op, op_val, step, inst)
                    self.env.set(inst.target, res)
                    trace.append(f"Step {step:04d} | PC {pc:03d} | {inst.target} = {inst.op} {repr(op_val)} -> {repr(res)}")
                    pc += 1

                # 4. Label Instruction (No-op at runtime)
                elif isinstance(inst, LabelInstruction):
                    trace.append(f"Step {step:04d} | PC {pc:03d} | LABEL {inst.label}")
                    pc += 1

                # 5. Unconditional Jump
                elif isinstance(inst, JumpInstruction):
                    target = inst.target_label
                    if target not in label_map:
                        raise ExecutionError(
                            f"Invalid jump target: Label '{target}' does not exist.",
                            instruction=inst,
                            step=step,
                        )
                    trace.append(f"Step {step:04d} | PC {pc:03d} | GOTO {target}")
                    pc = label_map[target] + 1

                # 6. Conditional Jump If False
                elif isinstance(inst, JumpIfFalseInstruction):
                    cond_val = self.resolve_operand(inst.condition)
                    if not isinstance(cond_val, bool):
                        raise ExecutionError(
                            f"Conditional jump requires boolean condition, got {type(cond_val).__name__}.",
                            instruction=inst,
                            step=step,
                        )
                    target = inst.target_label
                    if target not in label_map:
                        raise ExecutionError(
                            f"Invalid jump target: Label '{target}' does not exist.",
                            instruction=inst,
                            step=step,
                        )

                    if not cond_val:
                        trace.append(f"Step {step:04d} | PC {pc:03d} | IF_FALSE ({repr(cond_val)}) -> JUMP to {target}")
                        pc = label_map[target] + 1
                    else:
                        trace.append(f"Step {step:04d} | PC {pc:03d} | IF_FALSE ({repr(cond_val)}) -> Fallthrough")
                        pc += 1

                # 7. Conditional Jump If True
                elif isinstance(inst, JumpIfTrueInstruction):
                    cond_val = self.resolve_operand(inst.condition)
                    if not isinstance(cond_val, bool):
                        raise ExecutionError(
                            f"Conditional jump requires boolean condition, got {type(cond_val).__name__}.",
                            instruction=inst,
                            step=step,
                        )
                    target = inst.target_label
                    if target not in label_map:
                        raise ExecutionError(
                            f"Invalid jump target: Label '{target}' does not exist.",
                            instruction=inst,
                            step=step,
                        )

                    if cond_val:
                        trace.append(f"Step {step:04d} | PC {pc:03d} | IF_TRUE ({repr(cond_val)}) -> JUMP to {target}")
                        pc = label_map[target] + 1
                    else:
                        trace.append(f"Step {step:04d} | PC {pc:03d} | IF_TRUE ({repr(cond_val)}) -> Fallthrough")
                        pc += 1

                # 8. Function Call (User-Defined or Built-In)
                elif isinstance(inst, FunctionCallInstruction):
                    arg_vals = [self.resolve_operand(a) for a in inst.args]

                    # 8a. User-Defined Function Call
                    if inst.func_name in function_map:
                        func_info = function_map[inst.func_name]
                        params = func_info["params"]
                        if len(arg_vals) != len(params):
                            raise ExecutionError(
                                f"Function '{inst.func_name}' expects {len(params)} argument(s), got {len(arg_vals)}.",
                                instruction=inst,
                                step=step,
                            )
                        entry_label = func_info["entry_label"]
                        if entry_label not in label_map:
                            raise ExecutionError(
                                f"Function entry label '{entry_label}' does not exist for function '{inst.func_name}'.",
                                instruction=inst,
                                step=step,
                            )

                        args_repr = ", ".join(repr(a) for a in arg_vals)
                        trace.append(
                            f"Step {step:04d} | PC {pc:03d} | CALL {inst.func_name}({args_repr}) -> JUMP to {entry_label}"
                        )

                        # Push caller frame
                        call_stack.append((pc + 1, inst.target, self.env, inst.func_name))

                        # Create isolated local environment for the function
                        func_env = RuntimeEnvironment()
                        for p_name, a_val in zip(params, arg_vals):
                            func_env.set_input(p_name, a_val)

                        self.env = func_env
                        pc = label_map[entry_label] + 1
                        continue

                    # 8b. Built-In Function Call
                    res = self._execute_function_call(inst.func_name, arg_vals, step, inst)
                    self.env.set(inst.target, res)
                    args_repr = ", ".join(repr(a) for a in arg_vals)
                    trace.append(
                        f"Step {step:04d} | PC {pc:03d} | {inst.target} = {inst.func_name}({args_repr}) -> {repr(res)}"
                    )
                    pc += 1

                # 9. Return Instruction
                elif isinstance(inst, ReturnInstruction):
                    ret_val = self.resolve_operand(inst.value)
                    if not call_stack:
                        raise ExecutionError(
                            "RETURN instruction encountered without an active function call frame.",
                            instruction=inst,
                            step=step,
                        )
                    return_pc, target_var, caller_env, func_name = call_stack.pop()
                    caller_env.set(target_var, ret_val)
                    self.env = caller_env
                    trace.append(
                        f"Step {step:04d} | PC {pc:03d} | RETURN {repr(ret_val)} from {func_name} -> {target_var} in caller | Resume PC {return_pc:03d}"
                    )
                    pc = return_pc

                # 10. Function Boundary
                elif isinstance(inst, FunctionBoundaryInstruction):
                    prefix = "FUNC_START" if inst.is_start else "FUNC_END"
                    trace.append(f"Step {step:04d} | PC {pc:03d} | {prefix} {inst.name}")
                    pc += 1

                # 11. Rule Boundary
                elif isinstance(inst, RuleBoundaryInstruction):
                    boundary = "RULE_START" if inst.is_start else "RULE_END"
                    trace.append(f"Step {step:04d} | PC {pc:03d} | {boundary} {inst.name}")
                    pc += 1

                else:
                    pc += 1

            return ExecutionResult(
                status="success",
                outputs=self.env.get_outputs(),
                environment=self.env.snapshot(),
                step_count=step,
                trace=trace,
            )

        except ExecutionError as err:
            top_env = call_stack[0][2] if call_stack else self.env
            return ExecutionResult(
                status="failed",
                outputs=top_env.get_outputs(),
                environment=top_env.snapshot(),
                step_count=step,
                trace=trace,
                error=err.message,
                message=str(err),
            )

    def _execute_binary_op(
        self, op: str, left: Any, right: Any, step: int, inst: Instruction
    ) -> Any:
        """Execute a binary operation with strict type checking and division-by-zero detection."""
        # 1. Arithmetic Operators (+, -, *, /, %)
        if op in ("+", "-", "*", "/", "%"):
            # Booleans must never be coerced into numbers
            if isinstance(left, bool) or isinstance(right, bool):
                raise ExecutionError(
                    f"Operator '{op}' cannot be applied to boolean operands ({repr(left)}, {repr(right)}).",
                    instruction=inst,
                    step=step,
                )
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                raise ExecutionError(
                    f"Arithmetic operator '{op}' requires numeric operands, got {type(left).__name__} and {type(right).__name__}.",
                    instruction=inst,
                    step=step,
                )

            if op == "/":
                if right == 0:
                    raise ExecutionError("Division by zero", instruction=inst, step=step)
                return float(left) / float(right)

            if op == "%":
                if right == 0:
                    raise ExecutionError("Modulo by zero", instruction=inst, step=step)
                return left % right

            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right

        # 2. Relational Operators (<, <=, >, >=)
        if op in ("<", "<=", ">", ">="):
            if isinstance(left, bool) or isinstance(right, bool):
                raise ExecutionError(
                    f"Comparison operator '{op}' cannot be applied to boolean operands.",
                    instruction=inst,
                    step=step,
                )
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                raise ExecutionError(
                    f"Comparison operator '{op}' requires numeric operands, got {type(left).__name__} and {type(right).__name__}.",
                    instruction=inst,
                    step=step,
                )

            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            if op == ">=":
                return left >= right

        # 3. Equality Operators (==, !=)
        if op in ("==", "!="):
            # Strict type separation: bool cannot equal int/float; string cannot equal numeric
            if isinstance(left, bool) != isinstance(right, bool):
                are_equal = False
            elif isinstance(left, str) != isinstance(right, str):
                are_equal = False
            else:
                are_equal = (left == right)

            return are_equal if op == "==" else not are_equal

        # 4. Logical Operators (AND, OR)
        if op in ("AND", "OR"):
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise ExecutionError(
                    f"Logical operator '{op}' requires boolean operands, got {type(left).__name__} and {type(right).__name__}.",
                    instruction=inst,
                    step=step,
                )
            if op == "AND":
                return left and right
            if op == "OR":
                return left or right

        raise ExecutionError(
            f"Unsupported binary operator '{op}'.",
            instruction=inst,
            step=step,
        )

    def _execute_unary_op(
        self, op: str, val: Any, step: int, inst: Instruction
    ) -> Any:
        """Execute a unary operation."""
        if op in ("+", "-"):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ExecutionError(
                    f"Unary operator '{op}' requires numeric operand, got {type(val).__name__}.",
                    instruction=inst,
                    step=step,
                )
            return +val if op == "+" else -val

        if op == "NOT":
            if not isinstance(val, bool):
                raise ExecutionError(
                    f"Operator 'NOT' requires a boolean operand, got {type(val).__name__}.",
                    instruction=inst,
                    step=step,
                )
            return not val

        raise ExecutionError(
            f"Unsupported unary operator '{op}'.",
            instruction=inst,
            step=step,
        )

    def _execute_function_call(
        self, func_name: str, args: List[Any], step: int, inst: Instruction
    ) -> Any:
        """Execute a built-in function call."""
        fn = func_name.upper()
        if fn == "ABS":
            if len(args) != 1 or isinstance(args[0], bool) or not isinstance(args[0], (int, float)):
                raise ExecutionError(
                    f"Function ABS requires exactly 1 numeric argument, got {[type(a).__name__ for a in args]}.",
                    instruction=inst,
                    step=step,
                )
            res = abs(args[0])
            return float(res) if isinstance(args[0], float) else int(res)

        elif fn == "MIN":
            if len(args) != 2 or any(isinstance(a, bool) or not isinstance(a, (int, float)) for a in args):
                raise ExecutionError(
                    f"Function MIN requires 2 numeric arguments, got {[type(a).__name__ for a in args]}.",
                    instruction=inst,
                    step=step,
                )
            res = min(args[0], args[1])
            return float(res) if any(isinstance(a, float) for a in args) else int(res)

        elif fn == "MAX":
            if len(args) != 2 or any(isinstance(a, bool) or not isinstance(a, (int, float)) for a in args):
                raise ExecutionError(
                    f"Function MAX requires 2 numeric arguments, got {[type(a).__name__ for a in args]}.",
                    instruction=inst,
                    step=step,
                )
            res = max(args[0], args[1])
            return float(res) if any(isinstance(a, float) for a in args) else int(res)

        elif fn == "ROUND":
            if len(args) != 1 or isinstance(args[0], bool) or not isinstance(args[0], (int, float)):
                raise ExecutionError(
                    f"Function ROUND requires exactly 1 numeric argument, got {[type(a).__name__ for a in args]}.",
                    instruction=inst,
                    step=step,
                )
            return int(round(args[0]))

        elif fn == "LENGTH":
            if len(args) != 1 or not isinstance(args[0], str):
                raise ExecutionError(
                    f"Function LENGTH requires exactly 1 string argument, got {[type(a).__name__ for a in args]}.",
                    instruction=inst,
                    step=step,
                )
            return len(args[0])

        else:
            raise ExecutionError(
                f"Unknown built-in function '{func_name}'.",
                instruction=inst,
                step=step,
            )

