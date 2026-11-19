"""Three-Address Code (TAC) instruction definitions for RuleFlow IR."""

from typing import Any, Dict, List, Optional


class Constant:
    """Represents a compile-time constant literal value in TAC."""

    def __init__(self, value: Any):
        self.value = value

    def __repr__(self) -> str:
        if isinstance(self.value, str):
            return f'"{self.value}"'
        return str(self.value)

    def __str__(self) -> str:
        if isinstance(self.value, str):
            return f'"{self.value}"'
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Constant):
            # Ensure boolean values are not treated as equal to integer 1 or 0
            if isinstance(self.value, bool) or isinstance(other.value, bool):
                return (
                    isinstance(self.value, bool)
                    and isinstance(other.value, bool)
                    and self.value == other.value
                )
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)


def format_operand(operand: Any) -> str:
    """Format an operand (variable name, Constant, or raw value) for display."""
    if isinstance(operand, Constant):
        return str(operand)
    return str(operand)


class Instruction:
    """Base class for all Three-Address Code (TAC) instructions."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert instruction to dictionary for serialization and UI presentation."""
        return {
            "type": self.__class__.__name__,
            "text": str(self),
        }

    def __repr__(self) -> str:
        return str(self)


class AssignInstruction(Instruction):
    """Assignment instruction: target = source."""

    def __init__(self, target: str, source: Any):
        self.target = target
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": self.target,
            "op": "=",
            "arg1": str(self.source),
            "arg2": None,
        })
        return d

    def __str__(self) -> str:
        return f"{self.target} = {format_operand(self.source)}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AssignInstruction):
            return self.target == other.target and self.source == other.source
        return False


class BinaryOpInstruction(Instruction):
    """Binary operation instruction: target = left op right."""

    def __init__(self, target: str, op: str, left: Any, right: Any):
        self.target = target
        self.op = op
        self.left = left
        self.right = right

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": self.target,
            "op": self.op,
            "arg1": str(self.left),
            "arg2": str(self.right),
        })
        return d

    def __str__(self) -> str:
        return f"{self.target} = {format_operand(self.left)} {self.op} {format_operand(self.right)}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BinaryOpInstruction):
            return (
                self.target == other.target
                and self.op == other.op
                and self.left == other.left
                and self.right == other.right
            )
        return False


class UnaryOpInstruction(Instruction):
    """Unary operation instruction: target = op operand."""

    def __init__(self, target: str, op: str, operand: Any):
        self.target = target
        self.op = op
        self.operand = operand

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": self.target,
            "op": self.op,
            "arg1": str(self.operand),
            "arg2": None,
        })
        return d

    def __str__(self) -> str:
        op_prefix = f"{self.op} " if self.op.isalpha() else self.op
        return f"{self.target} = {op_prefix}{format_operand(self.operand)}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, UnaryOpInstruction):
            return (
                self.target == other.target
                and self.op == other.op
                and self.operand == other.operand
            )
        return False


class LabelInstruction(Instruction):
    """Label declaration instruction: LABEL label_name."""

    def __init__(self, label: str):
        self.label = label

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": None,
            "op": "LABEL",
            "arg1": self.label,
            "arg2": None,
        })
        return d

    def __str__(self) -> str:
        return f"LABEL {self.label}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, LabelInstruction):
            return self.label == other.label
        return False


class JumpInstruction(Instruction):
    """Unconditional jump instruction: GOTO target_label."""

    def __init__(self, target_label: str):
        self.target_label = target_label

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": None,
            "op": "GOTO",
            "arg1": self.target_label,
            "arg2": None,
        })
        return d

    def __str__(self) -> str:
        return f"GOTO {self.target_label}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, JumpInstruction):
            return self.target_label == other.target_label
        return False


class JumpIfFalseInstruction(Instruction):
    """Conditional jump if false: IF_FALSE condition GOTO target_label."""

    def __init__(self, condition: Any, target_label: str):
        self.condition = condition
        self.target_label = target_label

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": None,
            "op": "IF_FALSE",
            "arg1": str(self.condition),
            "arg2": self.target_label,
        })
        return d

    def __str__(self) -> str:
        return f"IF_FALSE {format_operand(self.condition)} GOTO {self.target_label}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, JumpIfFalseInstruction):
            return (
                self.condition == other.condition
                and self.target_label == other.target_label
            )
        return False


class JumpIfTrueInstruction(Instruction):
    """Conditional jump if true: IF_TRUE condition GOTO target_label."""

    def __init__(self, condition: Any, target_label: str):
        self.condition = condition
        self.target_label = target_label

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": None,
            "op": "IF_TRUE",
            "arg1": str(self.condition),
            "arg2": self.target_label,
        })
        return d

    def __str__(self) -> str:
        return f"IF_TRUE {format_operand(self.condition)} GOTO {self.target_label}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, JumpIfTrueInstruction):
            return (
                self.condition == other.condition
                and self.target_label == other.target_label
            )
        return False


class RuleBoundaryInstruction(Instruction):
    """Demarks the beginning or ending of a named rule."""

    def __init__(self, name: str, is_start: bool = True):
        self.name = name
        self.is_start = is_start

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": None,
            "op": "RULE_START" if self.is_start else "RULE_END",
            "arg1": self.name,
            "arg2": None,
        })
        return d

    def __str__(self) -> str:
        prefix = "RULE_START" if self.is_start else "RULE_END"
        return f"{prefix} {self.name}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, RuleBoundaryInstruction):
            return self.name == other.name and self.is_start == other.is_start
        return False


class FunctionCallInstruction(Instruction):
    """Function call instruction: target = func_name(arg1, arg2, ...)."""

    def __init__(self, target: str, func_name: str, args: List[Any]):
        self.target = target
        self.func_name = func_name
        self.args = list(args)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "target": self.target,
            "op": f"CALL {self.func_name}",
            "arg1": ", ".join(format_operand(a) for a in self.args),
            "arg2": None,
        })
        return d

    def __str__(self) -> str:
        formatted_args = ", ".join(format_operand(a) for a in self.args)
        return f"{self.target} = {self.func_name}({formatted_args})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FunctionCallInstruction):
            return (
                self.target == other.target
                and self.func_name == other.func_name
                and self.args == other.args
            )
        return False

