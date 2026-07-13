"""Lexer tests: token types, comments, string escapes, and lexical errors."""
import pytest

from src.lexer import Lexer, TokenType, LexerError


def types(source):
    return [t.type for t in Lexer(source).tokenize()]


def test_basic_token_types():
    assert types("Int x = 5;") == [
        TokenType.INT_TYPE,
        TokenType.IDENTIFIER,
        TokenType.EQUAL,
        TokenType.INTEGER,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]


def test_operators_and_multichar_tokens():
    assert types("a := b == c <= d .. e") == [
        TokenType.IDENTIFIER, TokenType.COLON_EQUAL,
        TokenType.IDENTIFIER, TokenType.EQUAL_EQUAL,
        TokenType.IDENTIFIER, TokenType.LESS_EQUAL,
        TokenType.IDENTIFIER, TokenType.DOT_DOT,
        TokenType.IDENTIFIER, TokenType.EOF,
    ]


def test_line_comments_are_skipped():
    tokens = Lexer("x // this is a comment\ny").tokenize()
    kinds = [t.type for t in tokens]
    assert kinds == [TokenType.IDENTIFIER, TokenType.IDENTIFIER, TokenType.EOF]
    # the comment is skipped but the newline still advances the line counter
    assert tokens[0].line == 1
    assert tokens[1].line == 2


def test_string_escape_sequences():
    # Aurora source is:  "a\nb\tc\"d\\e"
    tokens = Lexer(r'"a\nb\tc\"d\\e"').tokenize()
    assert tokens[0].type == TokenType.STRING
    assert tokens[0].value == 'a\nb\tc"d\\e'


def test_unterminated_string_raises():
    with pytest.raises(LexerError) as exc:
        Lexer('Int x = "oops').tokenize()
    assert exc.value.line == 1
    assert "Unterminated string" in str(exc.value)


def test_unknown_character_raises():
    with pytest.raises(LexerError) as exc:
        Lexer("Int x = @;").tokenize()
    assert "Unknown character" in str(exc.value)


def test_float_vs_integer_literals():
    tokens = Lexer("3 3.14").tokenize()
    assert tokens[0].type == TokenType.INTEGER and tokens[0].value == "3"
    assert tokens[1].type == TokenType.FLOAT and tokens[1].value == "3.14"
