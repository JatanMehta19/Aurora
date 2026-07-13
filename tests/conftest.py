"""Shared test fixtures for the Aurora test suite.

Ensures the repo root is importable (so ``aurora`` and the ``src`` package can
be imported) and exposes two ways of running Aurora source:

* ``run_captured`` — runs via :func:`aurora.run_source`, which swallows
  Lexer/Parser/Runtime errors and reports them through ``output_fn`` (this is
  exactly how the CLI behaves). Used for golden-output tests.
* ``run_raw`` — runs the Lexer → Parser → Interpreter pipeline directly so that
  errors *propagate* as exceptions. Used for behavior and error/type tests.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aurora import run_source          # noqa: E402
from src.lexer import Lexer            # noqa: E402
from src.parser import Parser          # noqa: E402
from src.interpreter import Interpreter  # noqa: E402

EXAMPLES_DIR = os.path.join(ROOT, "examples")
GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")


@pytest.fixture
def run_captured():
    """Return ``fn(source) -> list[str]`` capturing printed lines via run_source."""
    def _run(source):
        lines = []
        run_source(source, output_fn=lines.append)
        return lines
    return _run


@pytest.fixture
def run_raw():
    """Return ``fn(source) -> list[str]`` running the pipeline so errors propagate."""
    def _run(source):
        lines = []
        tokens = Lexer(source).tokenize()
        tree = Parser(tokens).parse()
        Interpreter(output_fn=lines.append).run(tree)
        return lines
    return _run
