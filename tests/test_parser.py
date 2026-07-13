"""Parser tests: operator precedence (AST shape) and parse-error line numbers."""
import pytest

from src.lexer import Lexer
from src.parser import Parser, ParseError
from src.ast_nodes import (
    Program, ExprStatement, BinaryExpression, UnaryExpression,
    IntegerLiteral, Identifier,
)


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def parse_expr(source):
    """Parse ``<source>;`` and return the single expression node."""
    prog = parse(source + ";")
    assert isinstance(prog, Program)
    stmt = prog.statements[0]
    assert isinstance(stmt, ExprStatement)
    return stmt.expression


def test_multiplication_binds_tighter_than_addition():
    # 2 + 3 * 4  ->  (+ 2 (* 3 4))
    e = parse_expr("2 + 3 * 4")
    assert isinstance(e, BinaryExpression) and e.operator == "+"
    assert isinstance(e.left, IntegerLiteral) and e.left.value == 2
    assert isinstance(e.right, BinaryExpression) and e.right.operator == "*"
    assert e.right.left.value == 3 and e.right.right.value == 4


def test_left_associativity_of_addition():
    # 2 * 3 + 4  ->  (+ (* 2 3) 4)
    e = parse_expr("2 * 3 + 4")
    assert e.operator == "+"
    assert isinstance(e.left, BinaryExpression) and e.left.operator == "*"
    assert isinstance(e.right, IntegerLiteral) and e.right.value == 4


def test_comparison_binds_looser_than_arithmetic():
    # 1 < 2 + 3  ->  (< 1 (+ 2 3))
    e = parse_expr("1 < 2 + 3")
    assert e.operator == "<"
    assert isinstance(e.right, BinaryExpression) and e.right.operator == "+"


def test_and_binds_tighter_than_or():
    # a and b or c  ->  (or (and a b) c)
    e = parse_expr("a and b or c")
    assert e.operator == "or"
    assert isinstance(e.left, BinaryExpression) and e.left.operator == "and"
    assert isinstance(e.right, Identifier) and e.right.name == "c"


def test_not_wraps_the_whole_equality():
    # not a == b  ->  (not (== a b))
    e = parse_expr("not a == b")
    assert isinstance(e, UnaryExpression) and e.operator == "not"
    assert isinstance(e.operand, BinaryExpression) and e.operand.operator == "=="


def test_parse_error_reports_correct_line():
    # error is on line 3 (the empty initializer)
    src = "Int a = 1;\nInt b = 2;\nInt c = ;\n"
    with pytest.raises(ParseError) as exc:
        parse(src)
    assert exc.value.line == 3


def test_parse_error_on_unclosed_paren():
    with pytest.raises(ParseError) as exc:
        parse('print("hi";')
    assert exc.value.line == 1
