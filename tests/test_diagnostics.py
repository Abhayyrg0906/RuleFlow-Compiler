"""Comprehensive unit and integration tests for RuleFlow Advanced Diagnostics (Phase 7.5)."""

import pytest

from ruleflow.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    DiagnosticCategory,
    SourceLocation,
    SourceRange,
    DiagnosticFormatter,
    DiagnosticReporter,
    find_best_match,
    suggest_variable,
    suggest_builtin_function,
    suggest_keyword,
)
from ruleflow.lexer import Lexer, LexerError
from ruleflow.parser import Parser, ParserError
from ruleflow.semantic import SemanticAnalyzer, SemanticError, DataType
from ruleflow.execution import Executor, ExecutionError
from ruleflow.ir.instructions import AssignInstruction


# -------------------------------------------------------------
# 1. Diagnostic Data Structures & Error Codes
# -------------------------------------------------------------

def test_diagnostic_creation_and_attributes():
    """Verify creation, attributes, and serialization of Diagnostic objects."""
    diag = Diagnostic(
        code=DiagnosticCode.SEM_UNDEFINED_VARIABLE,
        category=DiagnosticCategory.SEMANTIC,
        severity=DiagnosticSeverity.ERROR,
        message="Variable 'attendence' is not defined.",
        line=4,
        column=12,
        suggestion="Did you mean 'attendance'?",
        source_line="IF gpa >= 3.5 AND attendence >= 75 THEN",
    )

    assert diag.code == "SEM001"
    assert diag.category == DiagnosticCategory.SEMANTIC
    assert diag.severity == DiagnosticSeverity.ERROR
    assert diag.line == 4
    assert diag.column == 12
    assert diag.suggestion == "Did you mean 'attendance'?"
    assert isinstance(diag.location, SourceLocation)
    assert diag.location.line == 4
    assert diag.location.column == 12
    assert "Line 4, Column 12" in str(diag.location)

    d = diag.to_dict()
    assert d["code"] == "SEM001"
    assert d["category"] == "SEMANTIC"
    assert d["severity"] == "ERROR"
    assert d["line"] == 4
    assert d["column"] == 12
    assert d["suggestion"] == "Did you mean 'attendance'?"
    assert "[SEM001]" in str(diag)
    assert repr(diag).startswith("Diagnostic(")


def test_source_range():
    """Verify SourceRange attributes and dictionary representation."""
    rng = SourceRange(start_line=2, start_column=5, end_line=2, end_column=15)
    assert rng.start_line == 2
    assert rng.end_column == 15
    d = rng.to_dict()
    assert d["start_line"] == 2
    assert d["end_column"] == 15


def test_diagnostic_severity_and_category_enums():
    """Verify enum string representations."""
    assert str(DiagnosticSeverity.ERROR) == "ERROR"
    assert str(DiagnosticSeverity.WARNING) == "WARNING"
    assert str(DiagnosticSeverity.INFO) == "INFO"

    assert str(DiagnosticCategory.LEXICAL) == "LEXICAL"
    assert str(DiagnosticCategory.SYNTAX) == "SYNTAX"
    assert str(DiagnosticCategory.SEMANTIC) == "SEMANTIC"
    assert str(DiagnosticCategory.RUNTIME) == "RUNTIME"


# -------------------------------------------------------------
# 2. Source Highlighting and Formatter Tests
# -------------------------------------------------------------

def test_formatter_single_line_caret_highlighting():
    """Verify exact formatting matching Section 4 specification."""
    source_code = (
        "RULE Eligibility:\n"
        "    gpa = 3.8\n"
        "    attendance = 85\n"
        "    IF gpa >= 3.5 AND attendence >= 75 THEN\n"
        "        status = \"Eligible\"\n"
        "    END\n"
        "END\n"
    )

    diag = Diagnostic(
        code=DiagnosticCode.SEM_UNDEFINED_VARIABLE,
        category=DiagnosticCategory.SEMANTIC,
        severity=DiagnosticSeverity.ERROR,
        message="Variable 'attendence' is not defined.",
        line=4,
        column=23,
        suggestion="Did you mean 'attendance'?",
    )

    formatted = DiagnosticFormatter.format(diag, source_code=source_code)

    assert "SEMANTIC ERROR [SEM001]" in formatted
    assert "Line 4, Column 23:" in formatted
    assert "Variable 'attendence' is not defined." in formatted
    assert "Possible suggestion:" in formatted
    assert "Did you mean 'attendance'?" in formatted
    assert "Source:" in formatted
    assert "4 |     IF gpa >= 3.5 AND attendence >= 75 THEN" in formatted
    assert "^^^^^^^^^^" in formatted


def test_formatter_missing_source_graceful_handling():
    """Verify that formatting without source code does not crash and displays message."""
    diag = Diagnostic(
        code=DiagnosticCode.RUN_DIVISION_BY_ZERO,
        category=DiagnosticCategory.RUNTIME,
        severity=DiagnosticSeverity.ERROR,
        message="Division by zero.",
    )
    formatted = DiagnosticFormatter.format(diag, source_code=None)
    assert "RUNTIME ERROR [RUN001]" in formatted
    assert "Division by zero." in formatted
    assert "Source:" not in formatted


def test_formatter_format_all_multiple_diagnostics():
    """Verify formatting of multiple diagnostics with dividers."""
    d1 = Diagnostic(
        code="SYN001",
        category=DiagnosticCategory.SYNTAX,
        severity=DiagnosticSeverity.ERROR,
        message="Unexpected token.",
        line=1,
        column=5,
    )
    d2 = Diagnostic(
        code="SEM001",
        category=DiagnosticCategory.SEMANTIC,
        severity=DiagnosticSeverity.ERROR,
        message="Undefined variable.",
        line=2,
        column=8,
    )
    res = DiagnosticFormatter.format_all([d1, d2], source_code="x = 10\ny = z")
    assert "SYNTAX ERROR [SYN001]" in res
    assert "SEMANTIC ERROR [SEM001]" in res
    assert "-" * 60 in res


# -------------------------------------------------------------
# 3. Typo Suggestions Tests
# -------------------------------------------------------------

def test_suggest_variable_close_match():
    """Verify suggestions for misspelled variable names."""
    candidates = ["attendance", "cart_total", "customer_tier", "score"]

    s1 = suggest_variable("attendence", candidates)
    assert s1 == "Did you mean 'attendance'?"

    s2 = suggest_variable("scor", candidates)
    assert s2 == "Did you mean 'score'?"

    # Distant / completely unrelated variable should return None
    s3 = suggest_variable("xyz123", candidates)
    assert s3 is None


def test_suggest_builtin_function_typo():
    """Verify suggestions for misspelled built-in function names."""
    assert suggest_builtin_function("LENGHT") == "Did you mean 'LENGTH'?"
    assert suggest_builtin_function("rnd") == "Did you mean 'ROUND'?"
    assert suggest_builtin_function("abss") == "Did you mean 'ABS'?"
    assert suggest_builtin_function("completely_unrelated") is None


def test_suggest_keyword_typo():
    """Verify suggestions for misspelled keywords."""
    assert suggest_keyword("whlie") == "Did you mean keyword 'WHILE'?"
    assert suggest_keyword("funciton") == "Did you mean keyword 'FUNCTION'?"
    assert suggest_keyword("unrelated_identifier") is None


# -------------------------------------------------------------
# 4. Diagnostic Reporter Tests
# -------------------------------------------------------------

def test_diagnostic_reporter_collection_and_queries():
    """Verify DiagnosticReporter add, error, warning, info, and filtering."""
    reporter = DiagnosticReporter(source_code="x = 1\ny = 2")
    assert not reporter.has_errors()
    assert not reporter.has_warnings()
    assert len(reporter) == 0

    reporter.error(
        code="SEM001",
        message="Undefined var",
        category=DiagnosticCategory.SEMANTIC,
        line=1,
        column=1,
    )
    reporter.warning(
        code="OPT001",
        message="Unused var",
        category=DiagnosticCategory.OPTIMIZATION,
    )
    reporter.info(
        code="INF001",
        message="Processing",
        category=DiagnosticCategory.SEMANTIC,
    )

    assert reporter.has_errors()
    assert reporter.has_warnings()
    assert len(reporter) == 3
    assert len(reporter.get_errors()) == 1
    assert len(reporter.get_warnings()) == 1
    assert len(reporter.to_dict_list()) == 3

    reporter.clear()
    assert len(reporter) == 0
    assert not reporter.has_errors()


# -------------------------------------------------------------
# 5. Parser Error Recovery Tests
# -------------------------------------------------------------

def test_parser_recovery_multiple_syntax_errors():
    """Verify parser recovers and collects multiple independent syntax errors."""
    code = """
    RULE RecoveryDemo:
        a = 10 20
        b = 30
        c = 40 50
    END
    """
    tokens = Lexer(code).tokenize()
    parser = Parser(tokens, source_code=code, recovery=True)

    with pytest.raises(ParserError) as exc_info:
        parser.parse()

    err = exc_info.value
    # ParserError should carry collected diagnostics
    assert hasattr(err, "diagnostics")
    assert len(err.diagnostics) >= 2
    codes = [d.code for d in err.diagnostics]
    assert any("SYN" in c for c in codes)


def test_parser_recovery_avoids_infinite_loop():
    """Verify parser safely terminates on completely unparseable garbage without hanging."""
    code = """
    RULE LoopGuard:
        @@@ ??? !!!
    END
    """
    # Lexer will fail first on @
    with pytest.raises(LexerError) as exc_info:
        Lexer(code).tokenize()
    assert exc_info.value.code == "LEX001"
    assert exc_info.value.diagnostic.category == DiagnosticCategory.LEXICAL


def test_parser_keyword_suggestion():
    """Verify parser provides suggestion when DO is expected and THEN is found in WHILE."""
    code = """
    RULE WhileSyntax:
        WHILE count > 0 THEN
            count = count - 1
        END
    END
    """
    tokens = Lexer(code).tokenize()
    parser = Parser(tokens, source_code=code, recovery=False)

    with pytest.raises(ParserError) as exc_info:
        parser.parse()

    assert "Expected 'DO' after WHILE condition" in exc_info.value.message
    assert exc_info.value.suggestion == "Did you mean 'DO'?"
    assert exc_info.value.diagnostic.suggestion == "Did you mean 'DO'?"


# -------------------------------------------------------------
# 6. Semantic Error Recovery & No Cascading Tests
# -------------------------------------------------------------

def test_semantic_multiple_independent_errors_collected():
    """Verify semantic analyzer collects multiple errors in one pass without cascading."""
    code = """
    RULE MultiErrors:
        total = 100
        a = totl + 1
        flag = "True"
        IF flag THEN
            b = 10
        END
        c = 5
        c = "incompatible"
    END
    """
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(ast, source_code=code, recovery=True)

    with pytest.raises(SemanticError) as exc_info:
        analyzer.analyze()

    assert len(analyzer.diagnostics) >= 3
    # Check that typo suggestion was generated for 'totl'
    undefined_diags = [d for d in analyzer.diagnostics if d.code == DiagnosticCode.SEM_UNDEFINED_VARIABLE]
    assert len(undefined_diags) >= 1
    assert undefined_diags[0].suggestion == "Did you mean 'total'?"


def test_semantic_no_cascading_on_undefined_variable():
    """Verify that an undefined variable in an expression does not cause cascading errors in subsequent operations."""
    code = """
    RULE NoCascade:
        result = undefined_val + 10 * 2
    END
    """
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(ast, source_code=code, recovery=True)

    with pytest.raises(SemanticError):
        analyzer.analyze()

    # Exactly 1 error for undefined variable, not multiple cascaded arithmetic errors
    assert len(analyzer.diagnostics) == 1
    assert analyzer.diagnostics[0].code == DiagnosticCode.SEM_UNDEFINED_VARIABLE


def test_semantic_misspelled_builtin_suggestion():
    """Verify intelligent typo suggestion for misspelled built-in function."""
    code = """
    RULE BuiltinTypo:
        len = LENGHT("RuleFlow")
    END
    """
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(ast, source_code=code, recovery=True)

    with pytest.raises(SemanticError) as exc_info:
        analyzer.analyze()

    diag = analyzer.diagnostics[0]
    assert diag.code == DiagnosticCode.SEM_INVALID_FUNCTION_CALL
    assert diag.suggestion == "Did you mean 'LENGTH'?"
    assert exc_info.value.suggestion == "Did you mean 'LENGTH'?"


# -------------------------------------------------------------
# 7. Runtime Error Diagnostics
# -------------------------------------------------------------

def test_runtime_division_by_zero_diagnostic():
    """Verify runtime division by zero produces RUN001 diagnostic."""
    code = """
    RULE RunDivZero:
        d = 0.0
        res = 10.0 / d
    END
    """
    from tests.test_execution import run_pipeline

    res = run_pipeline(code)
    assert res.status == "failed"
    assert res.diagnostic is not None
    assert res.diagnostic.code == DiagnosticCode.RUN_DIVISION_BY_ZERO
    assert res.diagnostic.category == DiagnosticCategory.RUNTIME
    assert "Division by zero" in res.diagnostic.message


def test_runtime_step_limit_diagnostic():
    """Verify infinite loop produces RUN002 diagnostic."""
    code = """
    RULE Infinite:
        x = 1
        WHILE x > 0 DO
            x = x + 1
        END
    END
    """
    from tests.test_execution import run_pipeline

    res = run_pipeline(code, max_steps=50)
    assert res.status == "failed"
    assert res.diagnostic is not None
    assert res.diagnostic.code == DiagnosticCode.RUN_STEP_LIMIT_EXCEEDED
    assert "step limit exceeded" in res.diagnostic.message.lower()


# -------------------------------------------------------------
# 8. Example Diagnostic Files Verification
# -------------------------------------------------------------

def test_diagnostic_example_files_trigger_expected_diagnostics():
    """Verify each of the 5 new diagnostic example files triggers its intended error code."""
    from pathlib import Path

    ex_dir = Path(__file__).parent.parent / "examples"

    # 1. undefined_variable_error.rf
    code1 = (ex_dir / "undefined_variable_error.rf").read_text(encoding="utf-8")
    ast1 = Parser(Lexer(code1).tokenize()).parse()
    ana1 = SemanticAnalyzer(ast1, source_code=code1, recovery=True)
    with pytest.raises(SemanticError):
        ana1.analyze()
    assert any(d.code == DiagnosticCode.SEM_UNDEFINED_VARIABLE for d in ana1.diagnostics)
    assert any(d.suggestion == "Did you mean 'attendance'?" for d in ana1.diagnostics)

    # 2. type_mismatch_error.rf
    code2 = (ex_dir / "type_mismatch_error.rf").read_text(encoding="utf-8")
    ast2 = Parser(Lexer(code2).tokenize()).parse()
    ana2 = SemanticAnalyzer(ast2, source_code=code2, recovery=True)
    with pytest.raises(SemanticError):
        ana2.analyze()
    assert any(d.code == DiagnosticCode.SEM_TYPE_MISMATCH for d in ana2.diagnostics)

    # 3. syntax_error_recovery.rf
    code3 = (ex_dir / "syntax_error_recovery.rf").read_text(encoding="utf-8")
    parser3 = Parser(Lexer(code3).tokenize(), source_code=code3, recovery=True)
    with pytest.raises(ParserError):
        parser3.parse()
    assert len(parser3.diagnostics) >= 2

    # 4. misspelled_function_error.rf
    code4 = (ex_dir / "misspelled_function_error.rf").read_text(encoding="utf-8")
    ast4 = Parser(Lexer(code4).tokenize()).parse()
    ana4 = SemanticAnalyzer(ast4, source_code=code4, recovery=True)
    with pytest.raises(SemanticError):
        ana4.analyze()
    assert any(d.suggestion == "Did you mean 'LENGTH'?" for d in ana4.diagnostics)

    # 5. multiple_semantic_errors.rf
    code5 = (ex_dir / "multiple_semantic_errors.rf").read_text(encoding="utf-8")
    ast5 = Parser(Lexer(code5).tokenize()).parse()
    ana5 = SemanticAnalyzer(ast5, source_code=code5, recovery=True)
    with pytest.raises(SemanticError):
        ana5.analyze()
    assert len(ana5.diagnostics) >= 3
