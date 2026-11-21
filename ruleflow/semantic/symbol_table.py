"""Symbol and SymbolTable implementation for RuleFlow semantic analysis."""

from typing import Any, Dict, List, Optional, Tuple
from .types import DataType


class Symbol:
    """Represents a single variable entry in the symbol table."""

    def __init__(
        self,
        name: str,
        data_type: DataType,
        is_input: bool = False,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ):
        self.name = name
        self.data_type = data_type
        self.is_input = is_input
        self.line = line
        self.column = column

    def to_dict(self) -> Dict[str, Any]:
        """Convert symbol metadata into a dictionary representation."""
        return {
            "name": self.name,
            "type": self.data_type.value,
            "kind": "Input" if self.is_input else "Internal",
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        kind = "Input" if self.is_input else "Internal"
        return f"Symbol({self.name}: {self.data_type.value}, {kind}, line={self.line}, col={self.column})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Symbol):
            return (
                self.name == other.name
                and self.data_type == other.data_type
                and self.is_input == other.is_input
            )
        return False


class FunctionSymbol:
    """Represents a function declaration entry in the function symbol table."""

    def __init__(
        self,
        name: str,
        parameters: List[Tuple[str, DataType]],
        return_type: DataType,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ):
        self.name = name
        self.parameters = list(parameters)
        self.return_type = return_type
        self.line = line
        self.column = column

    def to_dict(self) -> Dict[str, Any]:
        """Convert function symbol metadata into a dictionary representation."""
        return {
            "name": self.name,
            "parameters": [
                {"name": name, "type": dtype.value}
                for name, dtype in self.parameters
            ],
            "return_type": self.return_type.value,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        param_strs = [f"{pname}: {ptype.value}" for pname, ptype in self.parameters]
        return f"FunctionSymbol({self.name}({', '.join(param_strs)}) -> {self.return_type.value})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FunctionSymbol):
            return (
                self.name == other.name
                and self.parameters == other.parameters
                and self.return_type == other.return_type
            )
        return False



class SymbolTable:
    """Scoped symbol table for tracking variable definitions and data types."""

    def __init__(self, parent: Optional["SymbolTable"] = None):
        self.parent: Optional["SymbolTable"] = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(
        self,
        name: str,
        data_type: DataType,
        is_input: bool = False,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> Symbol:
        """Register or update a symbol in the current scope."""
        symbol = Symbol(
            name=name,
            data_type=data_type,
            is_input=is_input,
            line=line,
            column=column,
        )
        self.symbols[name] = symbol
        return symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        """Search for a symbol in current and enclosing scopes."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def lookup_current(self, name: str) -> Optional[Symbol]:
        """Search for a symbol only within the immediate local scope."""
        return self.symbols.get(name)

    def is_defined(self, name: str) -> bool:
        """Check whether a variable name is visible in this scope."""
        return self.lookup(name) is not None

    def copy(self) -> "SymbolTable":
        """Create an isolated shallow copy of the symbol table with current definitions."""
        new_table = SymbolTable(parent=self.parent)
        for name, sym in self.symbols.items():
            new_table.symbols[name] = Symbol(
                name=sym.name,
                data_type=sym.data_type,
                is_input=sym.is_input,
                line=sym.line,
                column=sym.column,
            )
        return new_table

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary of all symbols defined in this table."""
        return {name: sym.to_dict() for name, sym in self.symbols.items()}

    def __repr__(self) -> str:
        return f"SymbolTable({list(self.symbols.keys())})"
