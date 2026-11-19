"""Runtime environment and variable storage for RuleFlow execution."""

import copy
import re
from typing import Any, Dict, Set
from .errors import ExecutionError


class RuntimeEnvironment:
    """Stores and manages variable state during RuleFlow program execution."""

    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.input_names: Set[str] = set()

    def set_input(self, name: str, value: Any) -> None:
        """Register an external input variable into the runtime environment."""
        self.input_names.add(name)
        self.variables[name] = value

    def set(self, name: str, value: Any) -> None:
        """Store or update a variable in the environment."""
        self.variables[name] = value

    def get(self, name: str) -> Any:
        """Retrieve the value of a variable, raising ExecutionError if undefined."""
        if name not in self.variables:
            raise ExecutionError(f"Variable '{name}' is undefined in runtime environment.")
        return self.variables[name]

    def has(self, name: str) -> bool:
        """Check if a variable exists in the environment."""
        return name in self.variables

    def get_outputs(self) -> Dict[str, Any]:
        """Return all user-visible named RuleFlow variables (excluding compiler temporaries)."""
        return {
            name: val
            for name, val in self.variables.items()
            if not bool(re.match(r"^t\d+$", name))
        }

    def get_internal_outputs(self) -> Dict[str, Any]:
        """Return only internally computed named variables (excluding external inputs and temporaries)."""
        return {
            name: val
            for name, val in self.variables.items()
            if not bool(re.match(r"^t\d+$", name)) and name not in self.input_names
        }

    def snapshot(self) -> Dict[str, Any]:
        """Return a safe deepcopy of the current variable state."""
        return copy.deepcopy(self.variables)

    def __repr__(self) -> str:
        return f"RuntimeEnvironment({self.variables})"
