"""Intermediate Representation (IR) package for RuleFlow Compiler."""

from .instructions import (
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
    format_operand,
)
from .ir_generator import IRGenerator

__all__ = [
    "Instruction",
    "Constant",
    "AssignInstruction",
    "BinaryOpInstruction",
    "UnaryOpInstruction",
    "LabelInstruction",
    "JumpInstruction",
    "JumpIfFalseInstruction",
    "JumpIfTrueInstruction",
    "RuleBoundaryInstruction",
    "FunctionCallInstruction",
    "format_operand",
    "IRGenerator",
]
