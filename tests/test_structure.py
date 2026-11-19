"""Basic structural tests for RuleFlow Compiler modules."""

from ruleflow.lexer import Lexer, Token
from ruleflow.ast import ASTNode, ProgramNode
from ruleflow.parser import Parser
from ruleflow.semantic import SemanticAnalyzer
from ruleflow.ir import IRGenerator
from ruleflow.optimizer import Optimizer
from ruleflow.codegen import CodeGenerator
from ruleflow.execution import Executor


def test_modules_instantiation():
    """Verify that all initial compiler modules can be instantiated."""
    lexer = Lexer("RULE Test:\n    status = \"Active\"")
    tokens = lexer.tokenize()
    assert isinstance(tokens, list)

    parser = Parser(tokens)
    ast = parser.parse()
    assert isinstance(ast, ProgramNode)

    analyzer = SemanticAnalyzer(ast)
    assert analyzer.analyze() is True

    ir_gen = IRGenerator(ast)
    ir_instructions = ir_gen.generate()
    assert isinstance(ir_instructions, list)

    optimizer = Optimizer(ir_instructions)
    opt_instructions = optimizer.optimize()
    assert isinstance(opt_instructions, list)

    codegen = CodeGenerator(opt_instructions)
    target_code = codegen.generate()
    assert target_code is not None

    executor = Executor(target_code)
    result = executor.execute()
    assert result["status"] in ("ready", "success")
