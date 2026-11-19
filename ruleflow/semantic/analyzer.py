"""Semantic analysis and type checking module for RuleFlow Compiler.

Performs:
- Scope resolution and symbol table management
- Variable declaration and definite assignment checking
- Strict type checking and widening verification
- Static detection of division or modulo by literal zero
"""

from typing import Any, Dict, List, Optional, Union
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
from .types import DataType
from .symbol_table import SymbolTable, Symbol
from .errors import SemanticError


class SemanticAnalyzer:
    """Performs contextual semantic analysis and type checking on a RuleFlow AST."""

    def __init__(
        self,
        ast: Optional[ProgramNode] = None,
        input_types: Optional[Dict[str, Union[DataType, str]]] = None,
    ):
        self.ast = ast
        self.input_types: Dict[str, DataType] = {}
        if input_types:
            for k, v in input_types.items():
                self.input_types[k] = DataType.from_value(v)

        # Map of rule name -> SymbolTable
        self.symbol_tables: Dict[str, SymbolTable] = {}
        # Backward-compatible dictionary representation of the active/last symbol table
        self.symbol_table: Dict[str, Any] = {}
        self.current_symbol_table: Optional[SymbolTable] = None

    def analyze(self, ast: Optional[ProgramNode] = None) -> bool:
        """Analyze the AST and populate symbol tables.

        Returns:
            True if semantic checks pass without errors.

        Raises:
            SemanticError: On any semantic or type violation.
        """
        tree_to_analyze = ast if ast is not None else self.ast
        if tree_to_analyze is None:
            return True

        self.symbol_tables.clear()
        self.symbol_table.clear()

        has_rules = any(isinstance(stmt, RuleDeclarationNode) for stmt in tree_to_analyze.statements)

        if has_rules:
            for stmt in tree_to_analyze.statements:
                if isinstance(stmt, RuleDeclarationNode):
                    self.analyze_rule(stmt)
                else:
                    # Non-rule statement alongside rules
                    if self.current_symbol_table is None:
                        self.current_symbol_table = self.create_initial_symbol_table()
                    self.analyze_statement(stmt)
        else:
            # Standalone statements outside any rule
            self.current_symbol_table = self.create_initial_symbol_table()
            self.symbol_tables["__global__"] = self.current_symbol_table
            for stmt in tree_to_analyze.statements:
                self.analyze_statement(stmt)
            self.symbol_table = self.current_symbol_table.to_dict()

        return True

    def create_initial_symbol_table(self) -> SymbolTable:
        """Create a new symbol table pre-populated with declared external inputs."""
        table = SymbolTable()
        for name, data_type in self.input_types.items():
            table.define(name, data_type, is_input=True)
        return table

    def analyze_rule(self, rule: RuleDeclarationNode) -> None:
        """Analyze a single RULE declaration in its own isolated scope."""
        rule_table = self.create_initial_symbol_table()
        self.symbol_tables[rule.name] = rule_table
        self.current_symbol_table = rule_table

        for stmt in rule.body:
            self.analyze_statement(stmt)

        # Expose active symbol table for UI / inspection
        self.symbol_table = rule_table.to_dict()

    def analyze_statement(self, stmt: ASTNode) -> None:
        """Dispatch statement analysis based on AST node type."""
        if isinstance(stmt, AssignmentNode):
            self.analyze_assignment(stmt)
        elif isinstance(stmt, IfStatementNode):
            self.analyze_if(stmt)
        elif isinstance(stmt, WhileStatementNode):
            self.analyze_while(stmt)
        elif isinstance(stmt, RuleDeclarationNode):
            self.analyze_rule(stmt)
        else:
            # Standalone expression statement
            self.analyze_expression(stmt)

    def analyze_assignment(self, node: AssignmentNode) -> None:
        """Analyze variable assignment and check type compatibility."""
        if self.current_symbol_table is None:
            self.current_symbol_table = self.create_initial_symbol_table()

        value_type = self.analyze_expression(node.value)

        existing_symbol = self.current_symbol_table.lookup(node.target)
        if existing_symbol is not None:
            # Reassignment: verify type compatibility
            if not existing_symbol.data_type.is_compatible_with(value_type):
                raise SemanticError(
                    f"Cannot assign {value_type.value} to {existing_symbol.data_type.value} variable '{node.target}'",
                    line=node.line,
                    column=node.column,
                    identifier=node.target,
                )
        else:
            # First assignment: introduce variable with inferred type
            self.current_symbol_table.define(
                name=node.target,
                data_type=value_type,
                is_input=False,
                line=node.line,
                column=node.column,
            )

    def analyze_if(self, node: IfStatementNode) -> None:
        """Analyze an IF-THEN-ELSE conditional statement and handle definite assignment."""
        if self.current_symbol_table is None:
            self.current_symbol_table = self.create_initial_symbol_table()

        # 1. Condition must be BOOLEAN
        condition_type = self.analyze_expression(node.condition)
        if condition_type != DataType.BOOLEAN:
            raise SemanticError(
                f"IF condition must evaluate to BOOLEAN, got {condition_type.value}",
                line=node.condition.line,
                column=node.condition.column,
            )

        base_table = self.current_symbol_table

        # 2. Analyze THEN branch in an isolated branched scope
        then_table = base_table.copy()
        self.current_symbol_table = then_table
        for stmt in node.then_branch:
            self.analyze_statement(stmt)

        # 3. Analyze each ELSE IF branch in an isolated branched scope
        elif_tables: List[SymbolTable] = []
        for elif_node in node.elif_branches:
            elif_cond_type = self.analyze_expression(elif_node.condition)
            if elif_cond_type != DataType.BOOLEAN:
                raise SemanticError(
                    f"ELSE IF condition must evaluate to BOOLEAN, got {elif_cond_type.value}",
                    line=elif_node.condition.line,
                    column=elif_node.condition.column,
                )
            elif_table = base_table.copy()
            self.current_symbol_table = elif_table
            for stmt in elif_node.body:
                self.analyze_statement(stmt)
            elif_tables.append(elif_table)

        # 4. Analyze ELSE branch (if present) in an isolated branched scope
        else_table: Optional[SymbolTable] = None
        if node.else_branch:
            else_table = base_table.copy()
            self.current_symbol_table = else_table
            for stmt in node.else_branch:
                self.analyze_statement(stmt)

        # Restore base scope
        self.current_symbol_table = base_table

        # 5. Definite assignment merge:
        # A variable introduced inside the conditional is only definitely assigned afterward
        # if it is assigned in ALL possible branches (THEN, all ELSE IFs, and ELSE) with compatible types.
        if else_table is not None:
            all_branch_tables = [then_table] + elif_tables + [else_table]

            candidate_vars = set(then_table.symbols.keys())
            for branch_tbl in all_branch_tables[1:]:
                candidate_vars &= set(branch_tbl.symbols.keys())

            for var_name in candidate_vars:
                first_sym = then_table.symbols[var_name]
                merged_type = first_sym.data_type

                for branch_tbl in all_branch_tables[1:]:
                    branch_sym = branch_tbl.symbols[var_name]
                    if merged_type == branch_sym.data_type:
                        continue
                    elif merged_type == DataType.INTEGER and branch_sym.data_type == DataType.DECIMAL:
                        merged_type = DataType.DECIMAL
                    elif merged_type == DataType.DECIMAL and branch_sym.data_type == DataType.INTEGER:
                        merged_type = DataType.DECIMAL
                    else:
                        raise SemanticError(
                            f"Variable '{var_name}' assigned with incompatible types across branches",
                            line=node.line,
                            column=node.column,
                            identifier=var_name,
                        )

                # Update or define in base scope
                existing_base = base_table.lookup(var_name)
                if existing_base is not None:
                    if not existing_base.data_type.is_compatible_with(merged_type):
                        raise SemanticError(
                            f"Cannot assign {merged_type.value} to {existing_base.data_type.value} variable '{var_name}'",
                            line=node.line,
                            column=node.column,
                            identifier=var_name,
                        )
                else:
                    base_table.define(
                        name=var_name,
                        data_type=merged_type,
                        is_input=False,
                        line=first_sym.line,
                        column=first_sym.column,
                    )

    def analyze_while(self, node: WhileStatementNode) -> None:
        """Analyze a WHILE loop statement and enforce definite assignment rules."""
        if self.current_symbol_table is None:
            self.current_symbol_table = self.create_initial_symbol_table()

        # 1. Condition must evaluate to BOOLEAN
        condition_type = self.analyze_expression(node.condition)
        if condition_type != DataType.BOOLEAN:
            raise SemanticError(
                f"WHILE condition must evaluate to BOOLEAN, got {condition_type.value}",
                line=node.condition.line,
                column=node.condition.column,
            )

        base_table = self.current_symbol_table

        # 2. Analyze loop body in an isolated branched scope
        loop_table = base_table.copy()
        self.current_symbol_table = loop_table
        for stmt in node.body:
            self.analyze_statement(stmt)

        # 3. Definite assignment:
        # A WHILE loop may execute zero times, so variables assigned only inside
        # the loop are NOT definitely assigned afterward. Restore base table.
        self.current_symbol_table = base_table

    def analyze_expression(self, node: ASTNode) -> DataType:
        """Infer and validate the data type of an expression node."""
        if isinstance(node, LiteralNode):
            if node.literal_type == "INTEGER":
                return DataType.INTEGER
            if node.literal_type == "DECIMAL":
                return DataType.DECIMAL
            if node.literal_type == "STRING":
                return DataType.STRING
            if node.literal_type == "BOOLEAN":
                return DataType.BOOLEAN
            raise SemanticError(
                f"Unknown literal type '{node.literal_type}'",
                line=node.line,
                column=node.column,
            )

        if isinstance(node, IdentifierNode):
            if self.current_symbol_table is None:
                raise SemanticError(
                    f"Undefined variable '{node.name}'",
                    line=node.line,
                    column=node.column,
                    identifier=node.name,
                )
            sym = self.current_symbol_table.lookup(node.name)
            if sym is None:
                raise SemanticError(
                    f"Undefined variable '{node.name}'",
                    line=node.line,
                    column=node.column,
                    identifier=node.name,
                )
            return sym.data_type

        if isinstance(node, FunctionCallNode):
            func_name = node.name.upper()
            if func_name not in ("ABS", "MIN", "MAX", "ROUND", "LENGTH"):
                raise SemanticError(
                    f"Unknown function '{node.name}'",
                    line=node.line,
                    column=node.column,
                )

            # 1. ABS(value): 1 numeric argument -> returns numeric type of argument
            if func_name == "ABS":
                if len(node.args) != 1:
                    raise SemanticError(
                        f"Function 'ABS' requires exactly 1 argument, got {len(node.args)}",
                        line=node.line,
                        column=node.column,
                    )
                arg_type = self.analyze_expression(node.args[0])
                if not arg_type.is_numeric():
                    raise SemanticError(
                        f"Function 'ABS' requires a numeric argument, got {arg_type.value}",
                        line=node.line,
                        column=node.column,
                    )
                return arg_type

            # 2. MIN(a, b): 2 numeric arguments -> returns DECIMAL if either is DECIMAL, else INTEGER
            if func_name == "MIN":
                if len(node.args) != 2:
                    raise SemanticError(
                        f"Function 'MIN' requires exactly 2 arguments, got {len(node.args)}",
                        line=node.line,
                        column=node.column,
                    )
                t1 = self.analyze_expression(node.args[0])
                t2 = self.analyze_expression(node.args[1])
                if not (t1.is_numeric() and t2.is_numeric()):
                    raise SemanticError(
                        f"Function 'MIN' requires numeric arguments, got {t1.value} and {t2.value}",
                        line=node.line,
                        column=node.column,
                    )
                if t1 == DataType.DECIMAL or t2 == DataType.DECIMAL:
                    return DataType.DECIMAL
                return DataType.INTEGER

            # 3. MAX(a, b): 2 numeric arguments -> returns DECIMAL if either is DECIMAL, else INTEGER
            if func_name == "MAX":
                if len(node.args) != 2:
                    raise SemanticError(
                        f"Function 'MAX' requires exactly 2 arguments, got {len(node.args)}",
                        line=node.line,
                        column=node.column,
                    )
                t1 = self.analyze_expression(node.args[0])
                t2 = self.analyze_expression(node.args[1])
                if not (t1.is_numeric() and t2.is_numeric()):
                    raise SemanticError(
                        f"Function 'MAX' requires numeric arguments, got {t1.value} and {t2.value}",
                        line=node.line,
                        column=node.column,
                    )
                if t1 == DataType.DECIMAL or t2 == DataType.DECIMAL:
                    return DataType.DECIMAL
                return DataType.INTEGER

            # 4. ROUND(value): 1 numeric argument -> returns INTEGER
            if func_name == "ROUND":
                if len(node.args) != 1:
                    raise SemanticError(
                        f"Function 'ROUND' requires exactly 1 argument, got {len(node.args)}",
                        line=node.line,
                        column=node.column,
                    )
                arg_type = self.analyze_expression(node.args[0])
                if not arg_type.is_numeric():
                    raise SemanticError(
                        f"Function 'ROUND' requires a numeric argument, got {arg_type.value}",
                        line=node.line,
                        column=node.column,
                    )
                return DataType.INTEGER

            # 5. LENGTH(text): 1 STRING argument -> returns INTEGER
            if func_name == "LENGTH":
                if len(node.args) != 1:
                    raise SemanticError(
                        f"Function 'LENGTH' requires exactly 1 argument, got {len(node.args)}",
                        line=node.line,
                        column=node.column,
                    )
                arg_type = self.analyze_expression(node.args[0])
                if arg_type != DataType.STRING:
                    raise SemanticError(
                        f"Function 'LENGTH' requires a STRING argument, got {arg_type.value}",
                        line=node.line,
                        column=node.column,
                    )
                return DataType.INTEGER

        if isinstance(node, UnaryOpNode):
            operand_type = self.analyze_expression(node.operand)
            if node.op in ("+", "-"):
                if not operand_type.is_numeric():
                    raise SemanticError(
                        f"Unary operator '{node.op}' requires numeric operand, got {operand_type.value}",
                        line=node.line,
                        column=node.column,
                        operator=node.op,
                    )
                return operand_type

            if node.op == "NOT":
                if operand_type != DataType.BOOLEAN:
                    raise SemanticError(
                        f"Operator NOT requires a BOOLEAN operand, got {operand_type.value}",
                        line=node.line,
                        column=node.column,
                        operator="NOT",
                    )
                return DataType.BOOLEAN

            raise SemanticError(
                f"Unsupported unary operator '{node.op}'",
                line=node.line,
                column=node.column,
                operator=node.op,
            )

        if isinstance(node, BinaryOpNode):
            left_type = self.analyze_expression(node.left)
            right_type = self.analyze_expression(node.right)
            op = node.op

            # 1. Arithmetic Operators (+, -, *, /, %)
            if op in ("+", "-", "*", "/", "%"):
                if not left_type.is_numeric() or not right_type.is_numeric():
                    raise SemanticError(
                        f"Arithmetic operator '{op}' requires numeric operands, got {left_type.value} and {right_type.value}",
                        line=node.line,
                        column=node.column,
                        operator=op,
                    )

                # Static literal zero detection
                if op in ("/", "%") and self.is_literal_zero(node.right):
                    op_label = "Division" if op == "/" else "Modulo"
                    raise SemanticError(
                        f"{op_label} by zero detected",
                        line=node.line,
                        column=node.column,
                        operator=op,
                    )

                # In RuleFlow, division always yields DECIMAL
                if op == "/":
                    return DataType.DECIMAL

                if left_type == DataType.DECIMAL or right_type == DataType.DECIMAL:
                    return DataType.DECIMAL
                return DataType.INTEGER

            # 2. Relational Operators (<, <=, >, >=)
            if op in ("<", "<=", ">", ">="):
                if not left_type.is_numeric() or not right_type.is_numeric():
                    raise SemanticError(
                        f"Relational operator '{op}' requires numeric operands, got {left_type.value} and {right_type.value}",
                        line=node.line,
                        column=node.column,
                        operator=op,
                    )
                return DataType.BOOLEAN

            # 3. Equality Operators (==, !=)
            if op in ("==", "!="):
                both_numeric = left_type.is_numeric() and right_type.is_numeric()
                both_string = (left_type == DataType.STRING and right_type == DataType.STRING)
                both_boolean = (left_type == DataType.BOOLEAN and right_type == DataType.BOOLEAN)

                if not (both_numeric or both_string or both_boolean):
                    raise SemanticError(
                        f"Type mismatch: cannot compare {left_type.value} with {right_type.value}",
                        line=node.line,
                        column=node.column,
                        operator=op,
                    )
                return DataType.BOOLEAN

            # 4. Logical Operators (AND, OR)
            if op in ("AND", "OR"):
                if left_type != DataType.BOOLEAN or right_type != DataType.BOOLEAN:
                    raise SemanticError(
                        f"Operator {op} requires BOOLEAN operands, got {left_type.value} and {right_type.value}",
                        line=node.line,
                        column=node.column,
                        operator=op,
                    )
                return DataType.BOOLEAN

            raise SemanticError(
                f"Unsupported binary operator '{op}'",
                line=node.line,
                column=node.column,
                operator=op,
            )

        raise SemanticError(
            f"Unable to analyze expression node of type '{node.__class__.__name__}'",
            line=node.line,
            column=node.column,
        )

    def is_literal_zero(self, node: ASTNode) -> bool:
        """Statically inspect whether an expression node is a literal zero."""
        if isinstance(node, LiteralNode):
            return node.value == 0 or node.value == 0.0
        if isinstance(node, UnaryOpNode) and node.op in ("+", "-"):
            return self.is_literal_zero(node.operand)
        return False
