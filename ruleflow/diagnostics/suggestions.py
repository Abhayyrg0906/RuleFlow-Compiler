"""Intelligent suggestion utilities using difflib for RuleFlow Compiler."""

import difflib
from typing import Iterable, List, Optional

BUILTIN_FUNCTIONS = ["ABS", "MIN", "MAX", "ROUND", "LENGTH"]

KEYWORDS = [
    "RULE",
    "IF",
    "THEN",
    "ELSE",
    "END",
    "WHILE",
    "DO",
    "FUNCTION",
    "RETURNS",
    "RETURN",
    "AND",
    "OR",
    "NOT",
    "INTEGER",
    "DECIMAL",
    "BOOLEAN",
    "STRING",
]


def find_best_match(
    target: str,
    candidates: Iterable[str],
    cutoff: float = 0.6,
) -> Optional[str]:
    """Find the single closest matching string among candidates using difflib.

    Args:
        target: The misspelled or unknown identifier.
        candidates: Candidate valid identifiers.
        cutoff: Minimum similarity threshold in [0.0, 1.0].

    Returns:
        The best matching candidate string, or None if no candidate passes the threshold.
    """
    if not target or not candidates:
        return None

    # Filter out exact matches or empty candidates
    unique_candidates = [c for c in set(candidates) if c and c != target]
    if not unique_candidates:
        return None

    # Case-insensitive check: if exact match ignoring case exists, return it
    lower_target = target.lower()
    for c in unique_candidates:
        if c.lower() == lower_target:
            return c

    # Use difflib close matches
    matches = difflib.get_close_matches(target, unique_candidates, n=1, cutoff=cutoff)
    if matches:
        return matches[0]

    # Try lowercase comparison for close matches
    lower_candidates = {c.lower(): c for c in unique_candidates}
    lower_matches = difflib.get_close_matches(lower_target, list(lower_candidates.keys()), n=1, cutoff=cutoff)
    if lower_matches:
        return lower_candidates[lower_matches[0]]

    return None


def suggest_variable(name: str, in_scope_variables: Iterable[str]) -> Optional[str]:
    """Suggest a similar variable name for an undefined variable."""
    match = find_best_match(name, in_scope_variables, cutoff=0.55)
    if match:
        return f"Did you mean '{match}'?"
    return None


def suggest_builtin_function(name: str) -> Optional[str]:
    """Suggest a similar built-in function name."""
    match = find_best_match(name.upper(), BUILTIN_FUNCTIONS, cutoff=0.5)
    if match:
        return f"Did you mean '{match}'?"
    return None


def suggest_keyword(token_str: str) -> Optional[str]:
    """Suggest a keyword for an unexpected token."""
    match = find_best_match(token_str.upper(), KEYWORDS, cutoff=0.6)
    if match:
        return f"Did you mean keyword '{match}'?"
    return None
