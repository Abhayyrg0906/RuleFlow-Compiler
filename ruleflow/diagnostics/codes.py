"""Stable diagnostic error codes for RuleFlow Compiler.

Categorized error code definitions:
- LEX: Lexical analysis errors
- SYN: Syntax / parsing errors
- SEM: Semantic analysis and type checking errors
- OPT: Optimization diagnostics
- GEN: Code generation diagnostics
- RUN: Runtime execution errors
"""


class DiagnosticCode:
    """Stable diagnostic error codes."""

    # Lexical Errors
    LEX_INVALID_CHAR = "LEX001"
    LEX_UNTERMINATED_STRING = "LEX002"
    LEX_INVALID_NUMBER = "LEX003"

    # Syntax Errors
    SYN_UNEXPECTED_TOKEN = "SYN001"
    SYN_MISSING_TOKEN = "SYN002"
    SYN_INVALID_STATEMENT = "SYN003"
    SYN_UNCLOSED_BLOCK = "SYN004"

    # Semantic Errors
    SEM_UNDEFINED_VARIABLE = "SEM001"
    SEM_TYPE_MISMATCH = "SEM002"
    SEM_DUPLICATE_DECLARATION = "SEM003"
    SEM_INVALID_RETURN = "SEM004"
    SEM_INVALID_FUNCTION_CALL = "SEM005"
    SEM_RECURSION_OR_CIRCULAR = "SEM006"
    SEM_ZERO_DIVISION_LITERAL = "SEM007"
    SEM_INDEFINITE_ASSIGNMENT = "SEM008"

    # Optimization Diagnostics
    OPT_DEAD_CODE = "OPT001"
    OPT_CONSTANT_CONDITION = "OPT002"

    # Code Generation Diagnostics
    GEN_INTERNAL_ERROR = "GEN001"

    # Runtime Execution Errors
    RUN_DIVISION_BY_ZERO = "RUN001"
    RUN_STEP_LIMIT_EXCEEDED = "RUN002"
    RUN_UNDEFINED_VARIABLE = "RUN003"
    RUN_TYPE_ERROR = "RUN004"
