"""Interpreter tests: closures, immutability, runtime errors, and recursion."""
import pytest

from src.environment import AuroraRuntimeError


def test_closure_captures_and_mutates_variable(run_raw):
    src = """
    func makeCounter() {
        Int mut count = 0;
        func inc() {
            count := count + 1;
            return count;
        }
        return inc;
    }
    auto c = makeCounter();
    print(str(c()));
    print(str(c()));
    print(str(c()));
    """
    assert run_raw(src) == ["1", "2", "3"]


def test_closures_are_independent(run_raw):
    src = """
    func makeCounter() {
        Int mut count = 0;
        func inc() { count := count + 1; return count; }
        return inc;
    }
    auto a = makeCounter();
    auto b = makeCounter();
    print(str(a()));
    print(str(a()));
    print(str(b()));
    """
    # b's counter is independent of a's
    assert run_raw(src) == ["1", "2", "1"]


def test_immutable_reassignment_is_rejected(run_raw):
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw("Int x = 5;\nx := 10;")
    assert "immutable" in str(exc.value)
    assert "[Line 2]" in str(exc.value)


def test_division_by_zero(run_raw):
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw("print(str(5 / 0));")
    assert "Division by zero" in str(exc.value)


def test_modulo_by_zero(run_raw):
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw("print(str(5 % 0));")
    assert "Modulo by zero" in str(exc.value)


def test_index_out_of_bounds(run_raw):
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw("List x = [1, 2, 3];\nprint(str(x[5]));")
    assert "out of bounds" in str(exc.value)


def test_undefined_variable(run_raw):
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw("print(str(nope));")
    assert "Undefined variable" in str(exc.value)
    assert "nope" in str(exc.value)


def test_undefined_property_on_instance(run_raw):
    src = """
    class Point {
        func init() { self.x := 1; }
    }
    auto p = Point();
    print(str(p.missing));
    """
    with pytest.raises(AuroraRuntimeError) as exc:
        run_raw(src)
    assert "missing" in str(exc.value)


def test_recursion_factorial(run_raw):
    src = """
    func factorial(Int n): Int {
        if n <= 1 { return 1; }
        return n * factorial(n - 1);
    }
    print(str(factorial(5)));
    print(str(factorial(10)));
    """
    assert run_raw(src) == ["120", "3628800"]


def test_recursion_fibonacci(run_raw):
    src = """
    func fib(Int n): Int {
        if n <= 1 { return n; }
        return fib(n - 1) + fib(n - 2);
    }
    print(str(fib(10)));
    """
    assert run_raw(src) == ["55"]
