"""Top-level execution facade for compiled RuleFlow instructions."""

from typing import Any, Dict, List, Optional
from ruleflow.semantic.types import DataType
from .runtime import RuntimeEnvironment
from .interpreter import TACInterpreter, ExecutionResult
from .errors import ExecutionError


class Executor:
    """Validates inputs, sets up runtime environment, and executes target instructions."""

    def __init__(
        self,
        target_code: Optional[List[Any]] = None,
        symbol_table: Optional[Dict[str, Any]] = None,
        max_steps: int = 10000,
    ):
        self.target_code = list(target_code) if target_code else []
        self.symbol_table = symbol_table or {}
        self.max_steps = max_steps
        self.environment = RuntimeEnvironment()

    def execute(self, inputs: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute compiled target code with optional runtime input variables.

        Args:
            inputs: Dictionary mapping external input variable names to runtime values.

        Returns:
            ExecutionResult containing execution status, named outputs, and trace.
        """
        # If no instructions are provided (e.g. skeleton tests), return ready status
        if not self.target_code:
            return ExecutionResult(
                status="ready",
                outputs={},
                environment={},
                step_count=0,
                message="Execution module initialized (no instructions to execute).",
            )

        provided_inputs = inputs or {}

        # Validate inputs against symbol table if symbol table metadata is provided
        try:
            self._validate_and_load_inputs(provided_inputs)
            interpreter = TACInterpreter(
                instructions=self.target_code,
                environment=self.environment,
                max_steps=self.max_steps,
            )
            return interpreter.execute()
        except ExecutionError as err:
            return ExecutionResult(
                status="failed",
                outputs=self.environment.get_outputs(),
                environment=self.environment.snapshot(),
                step_count=0,
                error=err.message,
                message=str(err),
                diagnostic=err.diagnostic,
            )

    def _validate_and_load_inputs(self, provided_inputs: Dict[str, Any]) -> None:
        """Validate input types and populate the runtime environment."""
        # Check required inputs defined in symbol table
        for name, sym_info in self.symbol_table.items():
            is_input = False
            expected_type_str = None

            if isinstance(sym_info, dict):
                is_input = sym_info.get("kind") == "Input" or sym_info.get("is_input") is True
                expected_type_str = sym_info.get("type")
            elif hasattr(sym_info, "is_input"):
                is_input = getattr(sym_info, "is_input", False)
                expected_type_str = str(getattr(sym_info, "data_type", ""))

            if is_input:
                if name not in provided_inputs:
                    raise ExecutionError(f"Missing required external input: '{name}'")

                val = provided_inputs[name]
                validated_val = self._validate_single_input(name, val, expected_type_str)
                self.environment.set_input(name, validated_val)

        # Also load any additional provided inputs that were not in the symbol table
        for name, val in provided_inputs.items():
            if not self.environment.has(name):
                self.environment.set_input(name, val)

    def _validate_single_input(self, name: str, val: Any, expected_type_str: Optional[str]) -> Any:
        """Check runtime type of input value and allow safe widening."""
        if not expected_type_str:
            return val

        expected_type = DataType.from_value(expected_type_str)

        if expected_type == DataType.INTEGER:
            # Must be integer and not boolean
            if isinstance(val, bool) or not isinstance(val, int):
                raise ExecutionError(
                    f"Invalid input type for '{name}': Expected INTEGER, got {type(val).__name__}."
                )
            return val

        if expected_type == DataType.DECIMAL:
            # Allow INTEGER widening to DECIMAL, but not boolean
            if isinstance(val, bool):
                raise ExecutionError(
                    f"Invalid input type for '{name}': Expected DECIMAL, got bool."
                )
            if isinstance(val, (int, float)):
                return float(val)
            raise ExecutionError(
                f"Invalid input type for '{name}': Expected DECIMAL, got {type(val).__name__}."
            )

        if expected_type == DataType.STRING:
            if not isinstance(val, str):
                raise ExecutionError(
                    f"Invalid input type for '{name}': Expected STRING, got {type(val).__name__}."
                )
            return val

        if expected_type == DataType.BOOLEAN:
            if not isinstance(val, bool):
                raise ExecutionError(
                    f"Invalid input type for '{name}': Expected BOOLEAN, got {type(val).__name__}."
                )
            return val

        return val
