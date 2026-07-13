from .lexer import TokenType, LexerError
from .ast_nodes import *

class ParseError(Exception):
    def __init__(self, msg, line):
        super().__init__(f"[Line {line}] Parse Error: {msg}")
        self.line = line

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens; self.pos = 0

    def cur(self): return self.tokens[self.pos]
    
    def peek(self, n=1):
        p = self.pos+n
        return self.tokens[p] if p < len(self.tokens) else self.tokens[-1]

    def advance(self):
        t = self.tokens[self.pos]
        if self.pos < len(self.tokens)-1: self.pos += 1
        return t

    def expect(self, *types):
        t = self.cur()
        if t.type not in types:
            exp = " or ".join(x.name for x in types)
            raise ParseError(f"Expected {exp} but got {t.type.name}('{t.value}')", t.line)
        return self.advance()

    def match(self, *types): return self.cur().type in types

    def is_type_kw(self):
        return self.match(TokenType.INT_TYPE, TokenType.FLOAT_TYPE, TokenType.STRING_TYPE,
                          TokenType.BOOL_TYPE, TokenType.LIST_TYPE, TokenType.MAP_TYPE, TokenType.AUTO)

    def parse(self):
        """program → declaration* EOF"""
        stmts = []
        while not self.match(TokenType.EOF): stmts.append(self.parse_decl())
        return Program(statements=stmts)

    def parse_decl(self):
        """declaration → funcDecl | classDecl | statement"""
        if self.match(TokenType.FUNC): return self.parse_func()
        if self.match(TokenType.CLASS): return self.parse_class()
        return self.parse_stmt()

    def parse_stmt(self):
        """statement → varDecl | if | while | for | return | break | import | print | exprStmt"""
        if self.is_type_kw(): return self.parse_var()
        if self.match(TokenType.IF): return self.parse_if()
        if self.match(TokenType.WHILE): return self.parse_while()
        if self.match(TokenType.FOR): return self.parse_for()
        if self.match(TokenType.RETURN): return self.parse_return()
        if self.match(TokenType.BREAK):
            self.advance(); self.expect(TokenType.SEMICOLON); return BreakStatement()
        if self.match(TokenType.IMPORT): return self.parse_import()
        if self.match(TokenType.PRINT): return self.parse_print()
        return self.parse_expr_stmt()

    def parse_var(self):
        """varDecl → type ('mut')? IDENTIFIER '=' expression ';'"""
        tok = self.advance(); type_name = tok.value
        mutable = bool(self.match(TokenType.MUT) and self.advance())
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.EQUAL)
        init = self.parse_expr()
        self.expect(TokenType.SEMICOLON)
        return VarDecl(type_name=type_name, name=name, mutable=mutable, initializer=init, line=tok.line)

    def parse_func(self):
        """funcDecl → 'func' IDENTIFIER '(' params? ')' (':' type)? block"""
        ftok = self.expect(TokenType.FUNC)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LPAREN)
        params = [] if self.match(TokenType.RPAREN) else self.parse_params()
        self.expect(TokenType.RPAREN)
        ret = None
        if self.match(TokenType.COLON): self.advance(); ret = self.advance().value
        self.expect(TokenType.LBRACE)
        body = self.parse_block()
        self.expect(TokenType.RBRACE)
        return FuncDecl(name=name, params=params, return_type=ret, body=body, line=ftok.line)

    def parse_params(self):
        """params → param (',' param)*"""
        params = []
        def one():
            tn = self.advance().value if self.is_type_kw() else None
            n = self.expect(TokenType.IDENTIFIER).value
            return Param(name=n, type_name=tn)
        params.append(one())
        while self.match(TokenType.COMMA): self.advance(); params.append(one())
        return params

    def parse_class(self):
        """classDecl → 'class' IDENTIFIER '{' funcDecl* '}'"""
        self.expect(TokenType.CLASS)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LBRACE)
        methods = []
        while not self.match(TokenType.RBRACE): methods.append(self.parse_func())
        self.expect(TokenType.RBRACE)
        return ClassDecl(name=name, methods=methods)

    def parse_if(self):
        """ifStmt → 'if' expression block ('else' ('if' ifStmt | block))?"""
        self.expect(TokenType.IF)
        cond = self.parse_expr()
        self.expect(TokenType.LBRACE); then = self.parse_block(); self.expect(TokenType.RBRACE)
        els = None
        if self.match(TokenType.ELSE):
            self.advance()
            if self.match(TokenType.IF): els = [self.parse_if()]
            else: self.expect(TokenType.LBRACE); els = self.parse_block(); self.expect(TokenType.RBRACE)
        return IfStatement(condition=cond, then_block=then, else_block=els)

    def parse_while(self):
        """whileStmt → 'while' expression block"""
        self.expect(TokenType.WHILE)
        cond = self.parse_expr()
        self.expect(TokenType.LBRACE); body = self.parse_block(); self.expect(TokenType.RBRACE)
        return WhileStatement(condition=cond, body=body)

    def parse_for(self):
        """forStmt → 'for' IDENTIFIER 'in' expression block"""
        self.expect(TokenType.FOR)
        var = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.IN)
        it = self.parse_expr()
        self.expect(TokenType.LBRACE); body = self.parse_block(); self.expect(TokenType.RBRACE)
        return ForStatement(variable=var, iterable=it, body=body)

    def parse_return(self):
        """returnStmt → 'return' expression? ';'"""
        self.expect(TokenType.RETURN)
        val = None if self.match(TokenType.SEMICOLON) else self.parse_expr()
        self.expect(TokenType.SEMICOLON)
        return ReturnStatement(value=val)

    def parse_import(self):
        """importStmt → 'import' IDENTIFIER ';'"""
        self.expect(TokenType.IMPORT)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.SEMICOLON)
        return ImportStatement(module_name=name)

    def parse_print(self):
        """printStmt → 'print' '(' expression ')' ';'"""
        self.expect(TokenType.PRINT)
        self.expect(TokenType.LPAREN)
        expr = self.parse_expr()
        self.expect(TokenType.RPAREN); self.expect(TokenType.SEMICOLON)
        return PrintStatement(expression=expr)

    def parse_expr_stmt(self):
        """exprStmt → expression ('=' expression)? ';'  (assignment or bare expr)"""
        ln = self.cur().line
        expr = self.parse_expr()
        if self.match(TokenType.COLON_EQUAL):
            self.advance(); val = self.parse_expr(); self.expect(TokenType.SEMICOLON)
            return AssignStatement(target=expr, value=val, line=ln)
        self.expect(TokenType.SEMICOLON)
        return ExprStatement(expression=expr)

    def parse_block(self):
        """block → statement* (until '}')"""
        stmts = []
        while not self.match(TokenType.RBRACE, TokenType.EOF): stmts.append(self.parse_decl())
        return stmts

    # ── Expression hierarchy (precedence: low to high) ──────────────────────
    def parse_expr(self): return self.parse_or()

    def parse_or(self):
        """expression → andExpr ('or' andExpr)*"""
        l = self.parse_and()
        while self.match(TokenType.OR):
            l = BinaryExpression(l, self.advance().value, self.parse_and())
        return l

    def parse_and(self):
        """andExpr → notExpr ('and' notExpr)*"""
        l = self.parse_not()
        while self.match(TokenType.AND):
            l = BinaryExpression(l, self.advance().value, self.parse_not())
        return l

    def parse_not(self):
        """notExpr → 'not' notExpr | equalityExpr"""
        if self.match(TokenType.NOT):
            return UnaryExpression(self.advance().value, self.parse_not())
        return self.parse_eq()

    def parse_eq(self):
        """equalityExpr → comparisonExpr (('==' | '!=') comparisonExpr)*"""
        l = self.parse_cmp()
        while self.match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            l = BinaryExpression(l, self.advance().value, self.parse_cmp())
        return l

    def parse_cmp(self):
        """comparisonExpr → additionExpr (('<'|'<='|'>'|'>='|'..') additionExpr)*"""
        l = self.parse_add()
        while self.match(TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL):
            l = BinaryExpression(l, self.advance().value, self.parse_add())
        if self.match(TokenType.DOT_DOT):
            l = BinaryExpression(l, self.advance().value, self.parse_add())
        return l

    def parse_add(self):
        """additionExpr → multiplicationExpr (('+' | '-') multiplicationExpr)*"""
        l = self.parse_mul()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            l = BinaryExpression(l, self.advance().value, self.parse_mul())
        return l

    def parse_mul(self):
        """multiplicationExpr → unaryExpr (('*' | '/' | '%') unaryExpr)*"""
        l = self.parse_unary()
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            l = BinaryExpression(l, self.advance().value, self.parse_unary())
        return l

    def parse_unary(self):
        """unaryExpr → '-' unaryExpr | callExpr"""
        if self.match(TokenType.MINUS):
            return UnaryExpression(self.advance().value, self.parse_unary())
        return self.parse_call()

    def parse_call(self):
        """callExpr → primaryExpr ( '(' args? ')' | '[' expr ']' | '.' IDENTIFIER )*"""
        expr = self.parse_primary()
        while True:
            if self.match(TokenType.LPAREN):
                self.advance()
                args = []
                if not self.match(TokenType.RPAREN):
                    args.append(self.parse_expr())
                    while self.match(TokenType.COMMA): self.advance(); args.append(self.parse_expr())
                self.expect(TokenType.RPAREN)
                expr = CallExpression(callee=expr, args=args)
            elif self.match(TokenType.LBRACKET):
                self.advance(); idx = self.parse_expr(); self.expect(TokenType.RBRACKET)
                expr = IndexAccess(obj=expr, index=idx)
            elif self.match(TokenType.DOT):
                self.advance(); name = self.expect(TokenType.IDENTIFIER).value
                expr = PropertyAccess(obj=expr, name=name)
            else:
                break
        return expr

    def parse_primary(self):
        """primaryExpr → literal | IDENTIFIER | '(' expression ')' | list | map"""
        t = self.cur()
        if t.type == TokenType.INTEGER: self.advance(); return IntegerLiteral(int(t.value))
        if t.type == TokenType.FLOAT: self.advance(); return FloatLiteral(float(t.value))
        if t.type == TokenType.STRING: self.advance(); return StringLiteral(t.value)
        if t.type == TokenType.TRUE: self.advance(); return BoolLiteral(True)
        if t.type == TokenType.FALSE: self.advance(); return BoolLiteral(False)
        if t.type == TokenType.NULL: self.advance(); return NullLiteral()
        if t.type == TokenType.IDENTIFIER: self.advance(); return Identifier(t.name if hasattr(t,"name") else t.value)
        if t.type == TokenType.LPAREN:
            self.advance(); e = self.parse_expr(); self.expect(TokenType.RPAREN); return e
        if t.type == TokenType.LBRACKET:
            self.advance(); elems = []
            if not self.match(TokenType.RBRACKET):
                elems.append(self.parse_expr())
                while self.match(TokenType.COMMA): self.advance(); elems.append(self.parse_expr())
            self.expect(TokenType.RBRACKET); return ListLiteral(elems)
        if t.type == TokenType.LBRACE:
            self.advance(); pairs = []
            if not self.match(TokenType.RBRACE):
                k = self.parse_expr(); self.expect(TokenType.COLON); v = self.parse_expr()
                pairs.append((k,v))
                while self.match(TokenType.COMMA):
                    self.advance(); k = self.parse_expr(); self.expect(TokenType.COLON); v = self.parse_expr()
                    pairs.append((k,v))
            self.expect(TokenType.RBRACE); return MapLiteral(pairs)
        raise ParseError(f"Unexpected token '{t.value}'", t.line)