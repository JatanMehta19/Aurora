"""Every runtime error reports the source line it occurred on.

Each source below deliberately places the failing construct on a line *other
than the first*, and asserts the exact line. A fixture whose error sits on line
1 would pass against an interpreter that hardcodes line 1, or one that is off by
one, so it would prove nothing.
"""
import pytest

from src.environment import AuroraRuntimeError


def _line_of(exc):
    """Extracts the reported line from a raised AuroraRuntimeError's message."""
    return str(exc.value).split("]")[0].lstrip("[").replace("Line ", "")


def _assert_line(exc, expected):
    assert f"[Line {expected}]" in str(exc.value), (
        f"expected line {expected}, got line {_line_of(exc)} "
        f"in message: {str(exc.value)!r}"
    )


# ── Arithmetic ──────────────────────────────────────────────────────────────

def test_division_by_zero_reports_line(run_raw):
    src = (
        "Int a = 10;\n"        # 1
        "Int b = 0;\n"         # 2
        "print(str(a / b));"   # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Division by zero" in str(exc.value)
    _assert_line(exc, 3)


def test_modulo_by_zero_reports_line(run_raw):
    src = (
        "Int a = 10;\n"        # 1
        "Int b = 0;\n"         # 2
        "print(str(a % b));"   # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Modulo by zero" in str(exc.value)
    _assert_line(exc, 3)


def test_binary_operator_type_error_reports_line(run_raw):
    src = (
        'String s = "hi";\n'   # 1
        "Int n = 3;\n"         # 2
        "print(str(s - n));"   # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    _assert_line(exc, 3)


def test_unary_minus_type_error_reports_line(run_raw):
    src = (
        'String s = "hi";\n'   # 1
        "Int n = 1;\n"         # 2
        "print(str(-s));"      # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    _assert_line(exc, 3)


# ── Collections ─────────────────────────────────────────────────────────────

def test_index_out_of_bounds_reports_line(run_raw):
    src = (
        "List xs = [1, 2, 3];\n"   # 1
        "Int i = 5;\n"             # 2
        "print(str(xs[i]));"       # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "out of bounds" in str(exc.value)
    _assert_line(exc, 3)


def test_missing_map_key_reports_line(run_raw):
    src = (
        'Map m = {"a": 1};\n'   # 1
        'String k = "b";\n'     # 2
        "print(str(m[k]));"     # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "not in Map" in str(exc.value)
    _assert_line(exc, 3)


def test_pop_on_empty_list_reports_line(run_raw):
    """Exercises a closure captured in _list_method, which has no node at call time."""
    src = (
        "List mut xs = [];\n"   # 1
        "Int n = 1;\n"          # 2
        "xs.pop();"             # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "pop on empty list" in str(exc.value)
    _assert_line(exc, 3)


def test_builtin_arg_error_reports_line(run_raw):
    """Exercises the _err() current_line fallback: builtins receive no node."""
    src = (
        "Int a = 1;\n"           # 1
        "Int b = 2;\n"           # 2
        "print(str(len(a)));"    # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "len()" in str(exc.value)
    _assert_line(exc, 3)


# ── Names and properties ────────────────────────────────────────────────────

def test_undefined_variable_reports_line(run_raw):
    src = (
        "Int a = 1;\n"          # 1
        "Int b = 2;\n"          # 2
        "print(str(nope));"     # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Undefined variable" in str(exc.value)
    _assert_line(exc, 3)


def test_undefined_property_reports_line(run_raw):
    src = (
        "class Point {\n"                       # 1
        "    func init() { self.x := 1; }\n"    # 2
        "}\n"                                   # 3
        "auto p = Point();\n"                   # 4
        "print(str(p.missing));"                # 5
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "missing" in str(exc.value)
    _assert_line(exc, 5)


# ── Control flow ────────────────────────────────────────────────────────────

def test_non_bool_if_condition_reports_line(run_raw):
    src = (
        "Int x = 5;\n"          # 1
        "if x {\n"              # 2
        '    print("hi");\n'    # 3
        "}"                     # 4
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "if condition must be Bool" in str(exc.value)
    _assert_line(exc, 2)


def test_non_bool_while_condition_reports_line(run_raw):
    src = (
        "Int x = 5;\n"      # 1
        "while x {\n"       # 2
        "    break;\n"      # 3
        "}"                 # 4
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "while condition must be Bool" in str(exc.value)
    _assert_line(exc, 2)


def test_iterating_non_iterable_reports_line(run_raw):
    src = (
        "Int x = 5;\n"          # 1
        "Int y = 6;\n"          # 2
        "for i in x {\n"        # 3
        "    print(str(i));\n"  # 4
        "}"                     # 5
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Cannot iterate" in str(exc.value)
    _assert_line(exc, 3)


# ── Calls ───────────────────────────────────────────────────────────────────

def test_wrong_arity_reports_call_site_not_declaration(run_raw):
    """The declaration is on line 1; the mistake is the caller's, on line 4."""
    src = (
        "func add(Int a, Int b): Int {\n"   # 1
        "    return a + b;\n"               # 2
        "}\n"                               # 3
        "print(str(add(1)));"               # 4
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "expects 2 args" in str(exc.value)
    _assert_line(exc, 4)


def test_wrong_argument_type_reports_call_site(run_raw):
    src = (
        "func needsInt(Int n): Int {\n"   # 1
        "    return n + 1;\n"             # 2
        "}\n"                             # 3
        'needsInt("hello");'              # 4
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Type error" in str(exc.value)
    _assert_line(exc, 4)


def test_calling_a_non_function_reports_line(run_raw):
    src = (
        "Int x = 5;\n"   # 1
        "Int y = 2;\n"   # 2
        "x();"           # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Cannot call" in str(exc.value)
    _assert_line(exc, 3)


def test_error_inside_function_body_reports_body_line(run_raw):
    """The failing expression is inside the callee, not at the call on line 5."""
    src = (
        "func f(Int n): Int {\n"   # 1
        "    Int z = 0;\n"         # 2
        "    return n / z;\n"      # 3
        "}\n"                      # 4
        "print(str(f(10)));"       # 5
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Division by zero" in str(exc.value)
    _assert_line(exc, 3)


def test_error_in_deeply_nested_call_reports_innermost_line(run_raw):
    """Recursion must not leave a stale line from an outer frame."""
    src = (
        "func inner(Int n): Int {\n"       # 1
        "    return n / 0;\n"              # 2
        "}\n"                              # 3
        "func outer(Int n): Int {\n"       # 4
        "    return inner(n);\n"           # 5
        "}\n"                              # 6
        "print(str(outer(1)));"            # 7
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    _assert_line(exc, 2)


# ── Types and mutability ────────────────────────────────────────────────────

def test_wrong_return_type_reports_line(run_raw):
    src = (
        "Int a = 1;\n"                            # 1
        'func giveInt(): Int { return "s"; }\n'   # 2
        "print(str(giveInt()));"                  # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Type error" in str(exc.value)
    _assert_line(exc, 2)


def test_reassign_wrong_type_reports_line(run_raw):
    src = (
        "Int a = 1;\n"              # 1
        "Int mut x = 5;\n"          # 2
        'x := "not an int";'        # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "Type error" in str(exc.value)
    _assert_line(exc, 3)


def test_immutable_reassignment_reports_line(run_raw):
    src = (
        "Int a = 1;\n"   # 1
        "Int x = 5;\n"   # 2
        "x := 10;"       # 3
    )
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "immutable" in str(exc.value)
    _assert_line(exc, 3)
