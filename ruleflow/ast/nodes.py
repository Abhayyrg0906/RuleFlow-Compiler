"""Abstract Syntax Tree (AST) node structures for RuleFlow Compiler.

Represents hierarchical syntactic structures of the RuleFlow source code.
Each node tracks line and column information for error reporting and debugging.
"""

from typing import Any, Dict, List, Optional


class ASTNode:
    """Base class for all Abstract Syntax Tree nodes."""

    def __init__(self, line: int = 1, column: int = 1):
        self.line = line
        self.column = column

    def to_dict(self) -> Dict[str, Any]:
        """Convert the AST node into a dictionary representation for serialization and visualization."""
        return {
            "node_type": self.__class__.__name__,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self, indent: int = 0) -> str:
        """Return a formatted, human-readable indented tree representation of the node."""
        space = "  " * indent
        return f"{space}{self.__class__.__name__}()"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__


class ProgramNode(ASTNode):
    """Root node representing an entire RuleFlow program consisting of rules or statements."""

    def __init__(self, statements: Optional[List[ASTNode]] = None, line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.statements: List[ASTNode] = statements or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "ProgramNode",
            "statements": [s.to_dict() for s in self.statements],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self, indent: int = 0) -> str:
        space = "  " * indent
        lines = [f"{space}ProgramNode ({len(self.statements)} statement{'s' if len(self.statements) != 1 else ''}):"]
        for stmt in self.statements:
            lines.append(stmt.pretty(indent + 1))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"ProgramNode(statements={len(self.statements)})"


class RuleDeclarationNode(ASTNode):
    """Represents a RULE declaration with a name and a body of statements."""

    def __init__(self, name: str, body: Optional[List[ASTNode]] = None, line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.name = name
        self.body: List[ASTNode] = body or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "RuleDeclarationNode",
            "name": self.name,
            "body": [stmt.to_dict() for stmt in self.body],
            "line": self.line,
            "column": self.column,
        }

    def pretty(self, indent: int = 0) -> str:
        space = "  " * indent
        lines = [f"{space}RuleDeclarationNode: '{self.name}' (line {self.line}, col {self.column})"]
        for stmt in self.body:
            lines.append(stmt.pretty(indent + 1))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"RuleDeclarationNode(name={repr(self.name)}, body={len(self.body)})"


class IfStatementNode(ASTNode):
    """Represents an IF-THEN-ELSE-END conditional statement."""

    def __init__(
        self,
        condition: ASTNode,
        then_branch: Optional[List[ASTNode]] = None,
        else_branch: Optional[List[ASTNode]] = None,
        line: int = 1,
        column: int = 1,
    ):
        super().__init__(line, column)
        self.condition = condition
        self.then_branch: List[ASTNode] = then_branch or []
        self.else_branch: List[ASTNode] = else_branch or []

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "node_type": "IfStatementNode",
            "condition": self.condition.to_dict(),
            "then_branch": [stmt.to_dict() for stmt in self.then_branch],
            "line": self.line,
            "column": self.column,
        }
        if self.else_branch:
            d["else_branch"] = [stmt.to_dict() for stmt in self.else_branch]
        return d

    def pretty(self, indent: int = 0) -> str:
        space = "  " * indent
        lines = [f"{space}IfStatementNode (line {self.line}, col {self.column}):"]
        lines.append(f"{space}  Condition:")
        lines.append(self.condition.pretty(indent + 2))
        lines.append(f"{space}  Then:")
        for stmt in self.then_branch:
            lines.append(stmt.pretty(indent + 2))
        if self.else_branch:
            lines.append(f"{space}  Else:")
            for stmt in self.else_branch:
                lines.append(stmt.pretty(indent + 2))
        return "\n".join(lines)

    def __repr__(self) -> str:
        has_else = len(self.else_branch) > 0
        return f"IfStatementNode(condition={self.condition}, then={len(self.then_branch)}, has_else={has_else})"


class AssignmentNode(ASTNode):
    """Represents a variable assignment statement (target = value)."""

    def __init__(self, target: str, value: ASTNode, line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.target = target
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "AssignmentNode",
            "target": self.target,
            "value": self.value.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def pretty(self, indent: int = 0) -> str:
        space = "  " * indent
        lines = [f"{space}AssignmentNode: {self.target} = (line {self.line}, col {self.column})"]
        lines.append(self.value.pretty(indent + 1))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"AssignmentNode(target={repr(self.target)}, value={self.value})"


class BinaryOpNode(ASTNode):
    """Represents a binary operation (arithmetic, relational, or logical)."""

    def __init__(self, left: ASTNode, op: str, right: ASTNode, line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.left = left
        self.op = op
        self.right = right

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "BinaryOpNode",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def pretty(self, indent: int = 0) -> str:
        space = "  " * indent
        lines = [f"{space}BinaryOpNode: '{self.op}' (line {self.line}, col {self.column})"]
        lines.append(self.left.pretty(indent + 1))
        lines.append(self.right.pretty(indent + 1))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"BinaryOpNode(left={self.left}, op={repr(self.op)}, right={self.right})"


class UnaryOpNode(ASTNode):
    """Represents a unary operation (e.g. '-' or 'NOT')."""

    def __init__(self, op: str, operand: ASTNode, line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.op = op
        self.operand = operand

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "UnaryOpNode",
            "op": self.op,
            "operand": self.operand.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def pretty(self, indent: int = 0) -> str:
        space = "  " * indent
        lines = [f"{space}UnaryOpNode: '{self.op}' (line {self.line}, col {self.column})"]
        lines.append(self.operand.pretty(indent + 1))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"UnaryOpNode(op={repr(self.op)}, operand={self.operand})"


class LiteralNode(ASTNode):
    """Represents a constant literal value (integer, decimal, or string)."""

    def __init__(self, value: Any, literal_type: str, line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.value = value
        self.literal_type = literal_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "LiteralNode",
            "literal_type": self.literal_type,
            "value": self.value,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self, indent: int = 0) -> str:
        space = "  " * indent
        return f"{space}LiteralNode({self.literal_type}: {repr(self.value)})"

    def __repr__(self) -> str:
        return f"LiteralNode({self.literal_type}, {repr(self.value)})"


class IdentifierNode(ASTNode):
    """Represents an identifier / variable reference."""

    def __init__(self, name: str, line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "IdentifierNode",
            "name": self.name,
            "line": self.line,
            "column": self.column,
        }

    def pretty(self, indent: int = 0) -> str:
        space = "  " * indent
        return f"{space}IdentifierNode('{self.name}')"

    def __repr__(self) -> str:
        return f"IdentifierNode({repr(self.name)})"
