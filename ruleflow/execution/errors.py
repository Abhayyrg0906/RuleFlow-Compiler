"""Runtime execution exception definitions for RuleFlow Compiler."""

from typing import Any, Optional


class ExecutionError(Exception):
    """Exception raised when runtime evaluation of RuleFlow instructions fails."""

    def __init__(
        self,
        message: str,
        instruction: Optional[Any] = None,
        step: Optional[int] = None,
    ):
        self.message = message
        self.instruction = instruction
        self.step = step
        loc = f"[Step {step}] " if step is not None else ""
        super().__init__(f"{loc}Execution Error: {message}")
