"""Intermediate Code Generation (IR) module for RuleFlow Compiler.

Translates verified Abstract Syntax Trees (AST) into a machine-independent
Three-Address Code (TAC) representation.
"""

from typing import Any, List, Optional
from ruleflow.ast.nodes import (
    ASTNode,
    ProgramNode,
    RuleDeclarationNode,
    IfStatementNode,
    WhileStatementNode,
    AssignmentNode,
    BinaryOpNode,
    UnaryOpNode,
    LiteralNode,
    IdentifierNode,
    FunctionCallNode,
)
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
)


class IRGenerator:
    """Generates Three-Address Code (TAC) instructions from a RuleFlow AST."""

    def __init__(self, ast: Optional[ProgramNode] = None):
        self.ast = ast
        self.instructions: List[Instruction] = []
        self.temp_counter: int = 0
        self.label_counter: int = 0

    def reset(self) -> None:
        """Reset internal counters and instruction stream."""
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0

    def new_temp(self) -> str:
        """Allocate a new temporary variable (e.g. t1, t2, ...)."""
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def new_label(self, prefix: str = "L") -> str:
        """Allocate a new unique control-flow label."""
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def emit(self, instruction: Instruction) -> None:
        """Append an instruction to the generated IR sequence."""
        self.instructions.append(instruction)

    def generate(self, ast: Optional[ProgramNode] = None) -> List[Instruction]:
        """Generate TAC instructions from the AST.

        Returns:
            List of generated TAC instructions.
        """
        self.reset()
        target_ast = ast if ast is not None else self.ast
        if target_ast is None:
            return []

        for stmt in target_ast.statements:
            self.generate_statement(stmt)

        return list(self.instructions)

    def generate_statement(self, stmt: ASTNode) -> None:
        """Dispatch generation for a statement node."""
        if isinstance(stmt, RuleDeclarationNode):
            self.generate_rule(stmt)
        elif isinstance(stmt, AssignmentNode):
            self.generate_assignment(stmt)
        elif isinstance(stmt, IfStatementNode):
            self.generate_if(stmt)
        elif isinstance(stmt, WhileStatementNode):
            self.generate_while(stmt)
        else:
            # Standalone expression
            self.generate_expression(stmt)

    def generate_rule(self, rule: RuleDeclarationNode) -> None:
        """Generate IR for a RULE block bounded by rule demarcations."""
        self.emit(RuleBoundaryInstruction(name=rule.name, is_start=True))
        for stmt in rule.body:
            self.generate_statement(stmt)
        self.emit(RuleBoundaryInstruction(name=rule.name, is_start=False))

    def generate_assignment(self, node: AssignmentNode) -> None:
        """Generate IR for variable assignment: target = expression."""
        val = self.generate_expression(node.value)
        self.emit(AssignInstruction(target=node.target, source=val))

    def generate_if(self, node: IfStatementNode) -> None:
        """Generate control-flow IR for conditional IF-THEN, IF-THEN-ELSE IF, and IF-THEN-ELSE statements."""
        end_label = self.new_label("L_end")
        has_elifs = bool(node.elif_branches)
        has_else = bool(node.else_branch)

        # Pre-allocate labels for each subsequent branch
        elif_labels = [self.new_label("L_elif") for _ in node.elif_branches]
        else_label = self.new_label("L_else") if has_else else None

        # 1. Initial IF branch
        next_target = elif_labels[0] if has_elifs else (else_label if has_else else end_label)
        cond_val = self.generate_expression(node.condition)
        self.emit(JumpIfFalseInstruction(condition=cond_val, target_label=next_target))
        for stmt in node.then_branch:
            self.generate_statement(stmt)
        if has_elifs or has_else:
            self.emit(JumpInstruction(target_label=end_label))

        # 2. Chained ELSE IF branches
        for i, elif_node in enumerate(node.elif_branches):
            self.emit(LabelInstruction(label=elif_labels[i]))
            is_last_branch = (i == len(node.elif_branches) - 1) and not has_else
            next_target = elif_labels[i + 1] if i + 1 < len(node.elif_branches) else (else_label if has_else else end_label)

            elif_cond_val = self.generate_expression(elif_node.condition)
            self.emit(JumpIfFalseInstruction(condition=elif_cond_val, target_label=next_target))
            for stmt in elif_node.body:
                self.generate_statement(stmt)
            if not is_last_branch:
                self.emit(JumpInstruction(target_label=end_label))

        # 3. Final ELSE branch (if present)
        if has_else and else_label is not None:
            self.emit(LabelInstruction(label=else_label))
            for stmt in node.else_branch:
                self.generate_statement(stmt)

        # 4. End label converging all branches
        self.emit(LabelInstruction(label=end_label))

    def generate_while(self, node: WhileStatementNode) -> None:
        """Generate control-flow IR for a WHILE loop statement."""
        start_label = self.new_label("L_while_start")
        end_label = self.new_label("L_while_end")

        self.emit(LabelInstruction(label=start_label))
        cond_val = self.generate_expression(node.condition)
        self.emit(JumpIfFalseInstruction(condition=cond_val, target_label=end_label))

        for stmt in node.body:
            self.generate_statement(stmt)

        self.emit(JumpInstruction(target_label=start_label))
        self.emit(LabelInstruction(label=end_label))

    def generate_expression(self, node: ASTNode) -> Any:
        """Generate TAC for an expression node, returning the result operand."""
        if isinstance(node, LiteralNode):
            return Constant(node.value)

        if isinstance(node, IdentifierNode):
            return node.name

        if isinstance(node, FunctionCallNode):
            arg_vals = [self.generate_expression(arg) for arg in node.args]
            temp = self.new_temp()
            self.emit(FunctionCallInstruction(target=temp, func_name=node.name.upper(), args=arg_vals))
            return temp

        if isinstance(node, UnaryOpNode):
            operand_val = self.generate_expression(node.operand)
            temp = self.new_temp()
            self.emit(UnaryOpInstruction(target=temp, op=node.op, operand=operand_val))
            return temp

        if isinstance(node, BinaryOpNode):
            # Short-circuit logical AND
            if node.op == "AND":
                left_val = self.generate_expression(node.left)
                temp = self.new_temp()
                false_label = self.new_label("L_false")
                end_label = self.new_label("L_and_end")

                self.emit(AssignInstruction(target=temp, source=left_val))
                self.emit(JumpIfFalseInstruction(condition=left_val, target_label=false_label))
                right_val = self.generate_expression(node.right)
                self.emit(AssignInstruction(target=temp, source=right_val))
                self.emit(JumpInstruction(target_label=end_label))

                self.emit(LabelInstruction(label=false_label))
                self.emit(AssignInstruction(target=temp, source=Constant(False)))
                self.emit(LabelInstruction(label=end_label))
                return temp

            # Short-circuit logical OR
            if node.op == "OR":
                left_val = self.generate_expression(node.left)
                temp = self.new_temp()
                true_label = self.new_label("L_true")
                end_label = self.new_label("L_or_end")

                self.emit(AssignInstruction(target=temp, source=left_val))
                self.emit(JumpIfTrueInstruction(condition=left_val, target_label=true_label))
                right_val = self.generate_expression(node.right)
                self.emit(AssignInstruction(target=temp, source=right_val))
                self.emit(JumpInstruction(target_label=end_label))

                self.emit(LabelInstruction(label=true_label))
                self.emit(AssignInstruction(target=temp, source=Constant(True)))
                self.emit(LabelInstruction(label=end_label))
                return temp

            # Arithmetic, relational, and equality operators
            left_val = self.generate_expression(node.left)
            right_val = self.generate_expression(node.right)
            temp = self.new_temp()
            self.emit(BinaryOpInstruction(target=temp, op=node.op, left=left_val, right=right_val))
            return temp

        return Constant(None)
