"""Source code snippet highlighting and diagnostic formatting for RuleFlow Compiler."""

import re
from typing import List, Optional
from .diagnostic import Diagnostic


class DiagnosticFormatter:
    """Formats compiler diagnostics with source line snippets and caret indicators."""

    @staticmethod
    def extract_source_line(source_code: str, line_number: int) -> Optional[str]:
        """Extract a single line from source code by 1-based line number."""
        if not source_code or line_number <= 0:
            return None
        lines = source_code.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return None

    @classmethod
    def format(
        cls,
        diagnostic: Diagnostic,
        source_code: Optional[str] = None,
    ) -> str:
        """Format a single Diagnostic with header, location, message, suggestion, and source snippet."""
        parts: List[str] = []

        # 1. Header: CATEGORY SEVERITY [CODE]
        header = f"{diagnostic.category.value} {diagnostic.severity.value} [{diagnostic.code}]"
        parts.append(header)
        parts.append("")

        # 2. Location & Message
        if diagnostic.line is not None and diagnostic.column is not None:
            parts.append(f"Line {diagnostic.line}, Column {diagnostic.column}:")
        elif diagnostic.line is not None:
            parts.append(f"Line {diagnostic.line}:")
        parts.append(diagnostic.message)

        # 3. Possible Suggestion
        if diagnostic.suggestion:
            parts.append("")
            parts.append("Possible suggestion:")
            parts.append(diagnostic.suggestion)

        # 4. Related Information
        if diagnostic.related_info:
            parts.append("")
            parts.append("Related information:")
            parts.append(diagnostic.related_info)

        # 5. Source Snippet with Caret Highlighting
        src_line = diagnostic.source_line
        if src_line is None and source_code is not None and diagnostic.line is not None:
            src_line = cls.extract_source_line(source_code, diagnostic.line)

        if src_line is not None and diagnostic.line is not None:
            parts.append("")
            parts.append("Source:")
            line_prefix = f"{diagnostic.line} | "
            parts.append(f"{line_prefix}{src_line}")

            if diagnostic.column is not None and diagnostic.column >= 1:
                # Calculate caret width
                col_idx = diagnostic.column - 1
                if diagnostic.end_column is not None and diagnostic.end_column > diagnostic.column:
                    caret_len = max(1, diagnostic.end_column - diagnostic.column)
                else:
                    # Infer token length from source line starting at column
                    rem = src_line[col_idx:] if col_idx < len(src_line) else ""
                    m = re.match(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]+", rem)
                    caret_len = len(m.group(0)) if m else 1

                caret_indent = " " * (len(line_prefix) + col_idx)
                carets = "^" * caret_len
                parts.append(f"{caret_indent}{carets}")

        # Multi-line snippet support if end_line is greater than line
        elif source_code is not None and diagnostic.line is not None and diagnostic.end_line is not None:
            if diagnostic.end_line > diagnostic.line:
                lines = source_code.splitlines()
                start_l = max(1, diagnostic.line)
                end_l = min(len(lines), diagnostic.end_line)
                parts.append("")
                parts.append("Source:")
                for l_num in range(start_l, end_l + 1):
                    parts.append(f"{l_num} | {lines[l_num - 1]}")

        return "\n".join(parts)

    @classmethod
    def format_all(
        cls,
        diagnostics: List[Diagnostic],
        source_code: Optional[str] = None,
    ) -> str:
        """Format a collection of diagnostics into a unified string separated by dividers."""
        if not diagnostics:
            return ""
        formatted_list = [cls.format(d, source_code=source_code) for d in diagnostics]
        return "\n\n" + ("-" * 60) + "\n\n".join([""] + formatted_list) + "\n"
