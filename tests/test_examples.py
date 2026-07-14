"""Golden-output tests: every program in examples/ must reproduce its snapshot.

The snapshots in tests/golden/*.out were generated from verified interpreter
output. Programs are run in-process via aurora.run_source (no shelling out).
"""
import os

import pytest

from conftest import EXAMPLES_DIR, GOLDEN_DIR

EXAMPLES = [
    "hello", "datatypes", "control", "functions", "classes", "errors", "fizzbuzz",
    "collections", "strings", "loops", "nested", "mutability",
]


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_all_examples_have_golden_files():
    """Guard against an example being added without a matching snapshot."""
    on_disk = {f[:-4] for f in os.listdir(EXAMPLES_DIR) if f.endswith(".aur")}
    assert on_disk == set(EXAMPLES)


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_matches_golden(name, run_captured):
    source = _read(os.path.join(EXAMPLES_DIR, name + ".aur"))
    expected = _read(os.path.join(GOLDEN_DIR, name + ".out")).splitlines()
    assert run_captured(source) == expected
