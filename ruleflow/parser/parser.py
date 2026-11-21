"""Recursive Descent Parser for the RuleFlow Compiler.

Translates a stream of tokens into an Abstract Syntax Tree (AST), enforcing
formal grammar rules for rule declarations, conditionals, assignments, and expressions.
"""

from typing import List, Optional
from ruleflow.lexer.lexer import Token
from ruleflow.lexer.token_types import TokenType
from ruleflow.ast.nodes import (
    ASTNode,
    ProgramNode,
    RuleDeclarationNode,
    IfStatementNode,
    ElseIfNode,
    WhileStatementNode,
    AssignmentNode,
    BinaryOpNode,
    UnaryOpNode,
    LiteralNode,
    IdentifierNode,
    FunctionCallNode,
    ParameterNode,
    ReturnStatementNode,
    FunctionDeclarationNode,
)
from .errors import ParserError


class Parser:
    """Recursive descent syntax analyzer for the RuleFlow language."""

    def __init__(self, tokens: Optional[List[Token]] = None):
        self.tokens: List[Token] = list(tokens) if tokens else []
        # Ensure there is always an EOF token at the end
        if not self.tokens or self.tokens[-1].type != TokenType.EOF:
            last_line = self.tokens[-1].line if self.tokens else 1
            last_col = self.tokens[-1].column if self.tokens else 1
            self.tokens.append(Token(TokenType.EOF, "", last_line, last_col))

        self.cursor: int = 0

    # ---------------------------------------------------------
    # Helper & Navigation Methods
    # ---------------------------------------------------------

    def current_token(self) -> Token:
        """Return the token at current position without advancing."""
        if self.cursor < len(self.tokens):
            return self.tokens[self.cursor]
        return self.tokens[-1]

    def peek(self, offset: int = 1) -> Token:
        """Look ahead by `offset` tokens without moving cursor."""
        idx = self.cursor + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def advance(self) -> Token:
        """Consume and return the current token, moving the cursor forward."""
        token = self.current_token()
        if self.cursor < len(self.tokens) - 1:
            self.cursor += 1
        return token

    def check(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given token types."""
        return self.current_token().type in token_types

    def match(self, *token_types: TokenType) -> Optional[Token]:
        """Consume and return current token if it matches any of token_types; else None."""
        if self.check(*token_types):
            return self.advance()
        return None

    def expect(self, expected_type: TokenType, error_message: str) -> Token:
        """Assert current token matches expected_type, consume it, or raise ParserError."""
        current = self.current_token()
        if current.type == expected_type:
            return self.advance()

        found_str = repr(current.value) if current.value else current.type.value
        raise ParserError(
            f"{error_message} (found: {found_str})",
            current.line,
            current.column,
            found_token=current,
        )

    # ---------------------------------------------------------
    # Parsing Methods (Recursive Descent Grammar)
    # ---------------------------------------------------------

    def parse(self) -> ProgramNode:
        """Parse the full token stream into a root ProgramNode."""
        statements: List[ASTNode] = []
        start_line = self.current_token().line
        start_col = self.current_token().column

        while not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            statements.append(stmt)

        return ProgramNode(statements=statements, line=start_line, column=start_col)

    def parse_statement(self) -> ASTNode:
        """Parse a top-level or block statement."""
        if self.check(TokenType.FUNCTION):
            return self.parse_function()
        if self.check(TokenType.RETURN):
            return self.parse_return()
        if self.check(TokenType.RULE):
            return self.parse_rule()
        if self.check(TokenType.IF):
            return self.parse_if()
        if self.check(TokenType.WHILE):
            return self.parse_while()
        if self.check(TokenType.IDENTIFIER) and self.peek().type == TokenType.ASSIGN:
            return self.parse_assignment()

        tok = self.current_token()
        raise ParserError(
            f"Unexpected token '{tok.value or tok.type.value}' at start of statement",
            tok.line,
            tok.column,
            found_token=tok,
        )

    def parse_rule(self) -> RuleDeclarationNode:
        """Parse a RULE declaration.

        Grammar:
            rule_declaration ::= RULE IDENTIFIER [COLON] statement* [END]
        """
        rule_tok = self.expect(TokenType.RULE, "Expected 'RULE' keyword")
        name_tok = self.expect(
            TokenType.IDENTIFIER,
            "Expected rule name identifier after 'RULE'",
        )

        # Optional colon after rule header
        if self.check(TokenType.COLON):
            self.advance()

        body: List[ASTNode] = []
        # Parse statements inside rule until EOF, another RULE, FUNCTION, or an explicit END
        while not self.check(TokenType.EOF, TokenType.RULE, TokenType.FUNCTION, TokenType.END):
            body.append(self.parse_statement())

        # Optional closing END for the rule declaration
        if self.check(TokenType.END):
            self.advance()

        return RuleDeclarationNode(
            name=name_tok.value,
            body=body,
            line=rule_tok.line,
            column=rule_tok.column,
        )

    def parse_if(self) -> IfStatementNode:
        """Parse an IF conditional statement with optional ELSE IF and ELSE branches.

        Grammar:
            if_statement ::= IF expression THEN statement*
                             (ELSE IF expression THEN statement*)*
                             (ELSE statement*)?
                             END
        """
        if_tok = self.expect(TokenType.IF, "Expected 'IF' keyword")
        condition = self.parse_expression()
        self.expect(TokenType.THEN, "Expected 'THEN' after IF condition")

        then_branch: List[ASTNode] = []
        while not self.check(TokenType.ELSE, TokenType.END, TokenType.EOF, TokenType.RULE):
            then_branch.append(self.parse_statement())

        elif_branches: List[ElseIfNode] = []
        # Support zero or more ELSE IF branches
        while self.check(TokenType.ELSE) and self.peek().type == TokenType.IF:
            else_tok = self.advance()  # consume ELSE
            self.advance()  # consume IF
            elif_cond = self.parse_expression()
            self.expect(TokenType.THEN, "Expected 'THEN' after ELSE IF condition")
            elif_body: List[ASTNode] = []
            while not self.check(TokenType.ELSE, TokenType.END, TokenType.EOF, TokenType.RULE):
                elif_body.append(self.parse_statement())
            elif_branches.append(
                ElseIfNode(
                    condition=elif_cond,
                    body=elif_body,
                    line=else_tok.line,
                    column=else_tok.column,
                )
            )

        # Optional final ELSE branch
        else_branch: List[ASTNode] = []
        if self.match(TokenType.ELSE):
            while not self.check(TokenType.END, TokenType.EOF, TokenType.RULE):
                else_branch.append(self.parse_statement())

        self.expect(TokenType.END, "Expected 'END' to close IF statement")

        return IfStatementNode(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            elif_branches=elif_branches,
            line=if_tok.line,
            column=if_tok.column,
        )

    def parse_while(self) -> WhileStatementNode:
        """Parse a WHILE loop statement.

        Grammar:
            while_statement ::= WHILE expression DO statement* END
        """
        while_tok = self.expect(TokenType.WHILE, "Expected 'WHILE' keyword")
        condition = self.parse_expression()
        self.expect(TokenType.DO, "Expected 'DO' after WHILE condition")

        body: List[ASTNode] = []
        while not self.check(TokenType.END, TokenType.EOF, TokenType.RULE):
            body.append(self.parse_statement())

        self.expect(TokenType.END, "Expected 'END' to close WHILE loop")

        return WhileStatementNode(
            condition=condition,
            body=body,
            line=while_tok.line,
            column=while_tok.column,
        )

    def parse_function(self) -> FunctionDeclarationNode:
        """Parse a FUNCTION declaration.

        Grammar:
            function_declaration ::=
                FUNCTION IDENTIFIER LPAREN parameter_list? RPAREN
                RETURNS type_name COLON
                function_body
                END
        """
        func_tok = self.expect(TokenType.FUNCTION, "Expected 'FUNCTION' keyword")
        name_tok = self.expect(
            TokenType.IDENTIFIER,
            "Expected function name identifier after 'FUNCTION'",
        )
        self.expect(TokenType.LPAREN, "Expected '(' after function name")

        parameters: List[ParameterNode] = []
        if not self.check(TokenType.RPAREN):
            while True:
                p_name = self.expect(TokenType.IDENTIFIER, "Expected parameter name")
                self.expect(TokenType.COLON, "Expected ':' after parameter name")
                p_type = self.expect(TokenType.IDENTIFIER, "Expected parameter type")
                parameters.append(
                    ParameterNode(
                        name=p_name.value,
                        data_type=p_type.value,
                        line=p_name.line,
                        column=p_name.column,
                    )
                )
                if self.check(TokenType.COMMA):
                    self.advance()
                else:
                    break

        self.expect(TokenType.RPAREN, "Expected ')' after parameter list")
        self.expect(TokenType.RETURNS, "Expected 'RETURNS' keyword in function declaration")
        ret_type_tok = self.expect(TokenType.IDENTIFIER, "Expected return type name after 'RETURNS'")
        self.expect(TokenType.COLON, "Expected ':' after return type")

        body: List[ASTNode] = []
        while not self.check(TokenType.END, TokenType.EOF, TokenType.RULE, TokenType.FUNCTION):
            body.append(self.parse_statement())

        self.expect(TokenType.END, "Expected 'END' to close FUNCTION declaration")

        return FunctionDeclarationNode(
            name=name_tok.value,
            parameters=parameters,
            return_type=ret_type_tok.value,
            body=body,
            line=func_tok.line,
            column=func_tok.column,
        )

    def parse_return(self) -> ReturnStatementNode:
        """Parse a RETURN statement.

        Grammar:
            return_statement ::= RETURN expression
        """
        ret_tok = self.expect(TokenType.RETURN, "Expected 'RETURN' keyword")
        expr = self.parse_expression()
        return ReturnStatementNode(expression=expr, line=ret_tok.line, column=ret_tok.column)

    def parse_assignment(self) -> AssignmentNode:
        """Parse a variable assignment.

        Grammar:
            assignment ::= IDENTIFIER '=' expression
        """
        target_tok = self.expect(TokenType.IDENTIFIER, "Expected identifier in assignment")
        self.expect(TokenType.ASSIGN, "Expected '=' in assignment")

        # Explicit check for missing value after '='
        if self.check(TokenType.EOF, TokenType.END, TokenType.ELSE, TokenType.RULE):
            tok = self.current_token()
            found_str = repr(tok.value) if tok.value else tok.type.value
            raise ParserError(
                f"Missing assignment value after '=' for variable '{target_tok.value}' (found: {found_str})",
                tok.line,
                tok.column,
                found_token=tok,
            )

        value_expr = self.parse_expression()

        return AssignmentNode(
            target=target_tok.value,
            value=value_expr,
            line=target_tok.line,
            column=target_tok.column,
        )

    # ---------------------------------------------------------
    # Expression Parsing (Precedence Hierarchy)
    # ---------------------------------------------------------

    def parse_expression(self) -> ASTNode:
        """Entry point for parsing expressions (lowest precedence: OR)."""
        return self.parse_or()

    def parse_or(self) -> ASTNode:
        """Logical OR expression: a OR b."""
        left = self.parse_and()

        while self.check(TokenType.OR):
            op_tok = self.advance()
            right = self.parse_and()
            left = BinaryOpNode(
                left=left,
                op=op_tok.value,
                right=right,
                line=op_tok.line,
                column=op_tok.column,
            )

        return left

    def parse_and(self) -> ASTNode:
        """Logical AND expression: a AND b."""
        left = self.parse_not()

        while self.check(TokenType.AND):
            op_tok = self.advance()
            right = self.parse_not()
            left = BinaryOpNode(
                left=left,
                op=op_tok.value,
                right=right,
                line=op_tok.line,
                column=op_tok.column,
            )

        return left

    def parse_not(self) -> ASTNode:
        """Logical NOT unary operator: NOT a."""
        if self.check(TokenType.NOT):
            op_tok = self.advance()
            operand = self.parse_not()
            return UnaryOpNode(
                op=op_tok.value,
                operand=operand,
                line=op_tok.line,
                column=op_tok.column,
            )

        return self.parse_relational()

    def parse_relational(self) -> ASTNode:
        """Relational comparison expressions: ==, !=, <, <=, >, >=."""
        left = self.parse_additive()

        while self.check(
            TokenType.EQUALS,
            TokenType.NOT_EQUALS,
            TokenType.LESS_THAN,
            TokenType.LESS_EQUAL,
            TokenType.GREATER_THAN,
            TokenType.GREATER_EQUAL,
        ):
            op_tok = self.advance()
            right = self.parse_additive()
            left = BinaryOpNode(
                left=left,
                op=op_tok.value,
                right=right,
                line=op_tok.line,
                column=op_tok.column,
            )

        return left

    def parse_additive(self) -> ASTNode:
        """Arithmetic addition and subtraction: +, -."""
        left = self.parse_multiplicative()

        while self.check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self.advance()
            right = self.parse_multiplicative()
            left = BinaryOpNode(
                left=left,
                op=op_tok.value,
                right=right,
                line=op_tok.line,
                column=op_tok.column,
            )

        return left

    def parse_multiplicative(self) -> ASTNode:
        """Arithmetic multiplication, division, and modulo: *, /, %."""
        left = self.parse_unary()

        while self.check(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op_tok = self.advance()
            right = self.parse_unary()
            left = BinaryOpNode(
                left=left,
                op=op_tok.value,
                right=right,
                line=op_tok.line,
                column=op_tok.column,
            )

        return left

    def parse_unary(self) -> ASTNode:
        """Unary arithmetic prefix operators: +, -."""
        if self.check(TokenType.MINUS, TokenType.PLUS):
            op_tok = self.advance()
            operand = self.parse_unary()
            return UnaryOpNode(
                op=op_tok.value,
                operand=operand,
                line=op_tok.line,
                column=op_tok.column,
            )

        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        """Primary expression: literals, identifiers, or parenthesized expressions."""
        tok = self.current_token()

        if self.match(TokenType.INTEGER):
            return LiteralNode(value=tok.value, literal_type="INTEGER", line=tok.line, column=tok.column)

        if self.match(TokenType.DECIMAL):
            return LiteralNode(value=tok.value, literal_type="DECIMAL", line=tok.line, column=tok.column)

        if self.match(TokenType.STRING):
            return LiteralNode(value=tok.value, literal_type="STRING", line=tok.line, column=tok.column)

        if self.check(TokenType.IDENTIFIER):
            id_tok = self.advance()
            # Check if this identifier is the start of a function call: name(...)
            if self.match(TokenType.LPAREN):
                args: List[ASTNode] = []
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        args.append(self.parse_expression())
                self.expect(
                    TokenType.RPAREN,
                    f"Expected ')' to close arguments for function '{id_tok.value}'",
                )
                return FunctionCallNode(
                    name=id_tok.value,
                    args=args,
                    line=id_tok.line,
                    column=id_tok.column,
                )
            return IdentifierNode(name=id_tok.value, line=id_tok.line, column=id_tok.column)

        if self.match(TokenType.LPAREN):
            opening_paren = tok
            expr = self.parse_expression()
            self.expect(
                TokenType.RPAREN,
                f"Expected ')' to close opening '(' from line {opening_paren.line}, col {opening_paren.column}",
            )
            return expr

        raise ParserError(
            f"Unexpected token in expression: '{tok.value or tok.type.value}'",
            tok.line,
            tok.column,
            found_token=tok,
        )
