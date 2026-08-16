import operator
from .ast_nodes import *
from .environment import Environment, AuroraRuntimeError

class ReturnException(Exception):
    """Unwinds call stack for return statements."""
    def __init__(self, v): self.value = v

class BreakException(Exception): 
    """Unwinds loop for break statements."""
    pass

class AuroraRange:
    """Represents a range expression (start..end) for for loops."""
    def __init__(self, s, e): self.start=s; self.end=e

class BuiltinFunction:
    """Wraps native Python functions as Aurora builtins."""
    def __init__(self, name, fn): self.name=name; self.fn=fn
    def call(self, args): return self.fn(args)
    def __repr__(self): return f"<builtin {self.name}>"

class AuroraFunction:
    """User-defined function with closure environment."""
    def __init__(self, decl, closure): self.declaration=decl; self.closure=closure
    def call(self, args, interp, line=None):
        env = Environment(self.closure)
        decl = self.declaration
        # Arity and argument-type errors are the *caller's* mistake, so they are
        # reported at the call site when one is known, not at the declaration.
        site = line if line is not None else decl.line
        if len(args) != len(decl.params):
            raise AuroraRuntimeError(f"\'{decl.name}\' expects {len(decl.params)} args, got {len(args)}", site)
        for p,a in zip(decl.params, args):
            if p.type_name is not None:  # untyped params (type_name None) accept anything
                interp._check_type(p.type_name, a, p.name, site)
            env.define(p.name, a, mutable=True, type_name=p.type_name)
        try: interp.exec_block(decl.body, env); result = None
        except ReturnException as r: result = r.value
        if decl.return_type is not None:  # enforce the declared return type
            interp._check_type(decl.return_type, result, f"return value of \'{decl.name}\'", decl.line)
        return result
    def bind(self, inst):
        """Creates a bound method with 'self' in its environment."""
        env = Environment(self.closure); env.define("self", inst, mutable=False)
        return BoundMethod(self.declaration, env)
    def __repr__(self): return f"<func {self.declaration.name}>"

class BoundMethod(AuroraFunction):
    def __repr__(self): return f"<method {self.declaration.name}>"

class AuroraClass:
    """Represents a class object with methods and closure."""
    def __init__(self, name, methods, closure):
        self.name=name; self.method_decls={m.name:m for m in methods}; self.closure=closure
    def call(self, args, interp, line=None):
        """Instantiate the class (calling it creates an instance)."""
        inst = AuroraInstance(self)
        init = self.method_decls.get("init")
        if init: AuroraFunction(init, self.closure).bind(inst).call(args, interp, line)
        return inst
    def __repr__(self): return f"<class {self.name}>"

class AuroraInstance:
    """Represents an instance of an Aurora class."""
    def __init__(self, klass): self.klass=klass; self.fields={}
    def get(self, name, line=None):
        if name in self.fields: return self.fields[name]
        m = self.klass.method_decls.get(name)
        if m: return AuroraFunction(m, self.klass.closure).bind(self)
        raise AuroraRuntimeError(f"\'{name}\' not found on {self.klass.name}", line)
    def set(self, name, val): self.fields[name] = val
    def __repr__(self): return f"<{self.klass.name} instance>"

class Interpreter:
    def __init__(self, output_fn=print):
        self.out = output_fn
        # Line of the most recently dispatched node. Used as a fallback by _err()
        # for the raise sites that have no AST node in scope — chiefly the builtin
        # and collection-method closures, which are called as bare BuiltinFunctions.
        self.current_line = None
        self.global_env = Environment(type_checker=self._check_type)
        self._builtins()

    def _err(self, msg, line=None):
        """Builds an AuroraRuntimeError, falling back to the last dispatched line."""
        return AuroraRuntimeError(msg, line if line is not None else self.current_line)

    def _builtins(self):
        """Registers built-in functions (len, type, int, float, str, bool)."""
        def bl(n,f): self.global_env.define(n, BuiltinFunction(n,f), mutable=False)
        def _conv(name, fn, a):
            """Wraps int()/float() so bad input raises a clean AuroraRuntimeError, not a Python one."""
            if len(a)!=1: raise self._err(f"{name}() expects 1 arg")
            try: return fn(a[0])
            except (ValueError, TypeError): raise self._err(f"Cannot convert {self._tname(a[0])} to {name.capitalize()}")
        bl("len",   lambda a: len(a[0]) if len(a)==1 and isinstance(a[0],(str,list,dict)) else (_ for _ in ()).throw(self._err("len() expects 1 collection arg")))
        bl("type",  lambda a: self._tname(a[0]) if len(a)==1 else (_ for _ in ()).throw(self._err("type() expects 1 arg")))
        bl("int",   lambda a: _conv("int", int, a))
        bl("float", lambda a: _conv("float", float, a))
        bl("str",   lambda a: self._str(a[0]) if len(a)==1 else (_ for _ in ()).throw(self._err("str() expects 1 arg")))
        bl("bool",  lambda a: bool(a[0]) if len(a)==1 else (_ for _ in ()).throw(self._err("bool() expects 1 arg")))

    def _tname(self, v):
        """Maps Python types to Aurora type names (Int, Float, String, etc.)."""
        if v is None: return "Null"
        if isinstance(v, bool): return "Bool"
        if isinstance(v, int): return "Int"
        if isinstance(v, float): return "Float"
        if isinstance(v, str): return "String"
        if isinstance(v, list): return "List"
        if isinstance(v, dict): return "Map"
        if isinstance(v, AuroraInstance): return v.klass.name
        if isinstance(v, AuroraClass): return f"Class<{v.name}>"
        return "Function"

    def _str(self, v):
        """Converts a value to its Aurora string representation."""
        if v is None: return "null"
        if isinstance(v, bool): return "true" if v else "false"
        if isinstance(v, list): return "[" + ", ".join(self._str(x) for x in v) + "]"
        if isinstance(v, dict):
            return "{" + ", ".join(f"{self._str(k)}: {self._str(v2)}" for k,v2 in v.items()) + "}"
        if isinstance(v, AuroraInstance): return f"<{v.klass.name}>"
        return str(v)

    def _check_type(self, tname, val, name, line=None):
        """Validates that a value matches its declared type (var decls, reassignment,
        function parameters, and return values). 'auto'/None types are unchecked."""
        ok = {"Int": lambda v: isinstance(v,int) and not isinstance(v,bool),
              "Float": lambda v: isinstance(v,(int,float)) and not isinstance(v,bool),
              "String": lambda v: isinstance(v,str),
              "Bool": lambda v: isinstance(v,bool),
              "List": lambda v: isinstance(v,list),
              "Map": lambda v: isinstance(v,dict)}
        chk = ok.get(tname)
        if chk and not chk(val):
            raise self._err(f"Type error: \'{name}\' declared as {tname} but got {self._tname(val)}", line)

    def _coerce(self, tname, val):
        """Coerces an Int to a Float when the declared type is Float (5 -> 5.0)."""
        if tname == "Float" and isinstance(val, int) and not isinstance(val, bool): return float(val)
        return val

    def _mapkey(self, key, line=None):
        """Validates that a value can be used as a Map key (List/Map are unhashable)."""
        if isinstance(key, (list, dict)):
            raise self._err(f"Map key must be a hashable type (Int, Float, String, or Bool), got {self._tname(key)}", line)
        return key

    def run(self, program): self.exec_block(program.statements, self.global_env)

    def exec_block(self, stmts, env):
        for s in stmts: self.exec(s, env)

    def exec(self, node, env):
        """Dispatches to exec_<NodeType> method."""
        self._track(node)
        fn = getattr(self, f"exec_{type(node).__name__}", None)
        if fn: return fn(node, env)
        raise self._err(f"Unknown node: {type(node).__name__}")

    def _track(self, node):
        """Records the node's line so _err() can attribute node-less raises."""
        line = getattr(node, "line", None)
        if line is not None: self.current_line = line

    # ── Statement executors ────────────────────────────────────────────────
    def exec_VarDecl(self, n, env):
        """Handles VarDecl: evaluates initializer, checks type, defines variable."""
        v = self.eval(n.initializer, env); self._check_type(n.type_name, v, n.name, n.line)
        v = self._coerce(n.type_name, v)
        env.define(n.name, v, mutable=n.mutable, type_name=n.type_name)

    def exec_AssignStatement(self, n, env):
        """Handles assignment: supports Identifier, IndexAccess, and PropertyAccess targets."""
        v = self.eval(n.value, env); t = n.target
        if isinstance(t, Identifier): env.assign(t.name, v, n.line)
        elif isinstance(t, IndexAccess):
            obj=self.eval(t.obj,env); idx=self.eval(t.index,env)
            if isinstance(obj,list):
                if not isinstance(idx,int) or isinstance(idx,bool): raise self._err("List index must be Int", n.line)
                if idx<0 or idx>=len(obj): raise self._err(f"Index {idx} out of bounds", n.line)
                obj[idx]=v
            elif isinstance(obj,dict): obj[self._mapkey(idx, n.line)]=v
            else: raise self._err("Cannot index-assign non-List/Map", n.line)
        elif isinstance(t, PropertyAccess):
            obj=self.eval(t.obj,env)
            if isinstance(obj,AuroraInstance): obj.set(t.name,v)
            else: raise self._err(f"Cannot set property on {self._tname(obj)}", n.line)
        else: raise self._err("Invalid assignment target", n.line)

    def exec_PrintStatement(self, n, env): self.out(self._str(self.eval(n.expression, env)))
    def exec_ExprStatement(self, n, env): self.eval(n.expression, env)

    def exec_IfStatement(self, n, env):
        """Handles if/else: condition must evaluate to Bool."""
        cond = self.eval(n.condition, env)
        if not isinstance(cond, bool): raise self._err(f"if condition must be Bool, got {self._tname(cond)}", n.line)
        if cond: self.exec_block(n.then_block, Environment(env))
        elif n.else_block is not None: self.exec_block(n.else_block, Environment(env))

    def exec_WhileStatement(self, n, env):
        """Handles while loops: condition must be Bool, supports break."""
        while True:
            cond = self.eval(n.condition, env)
            if not isinstance(cond, bool): raise self._err(f"while condition must be Bool, got {self._tname(cond)}", n.line)
            if not cond: break
            try: self.exec_block(n.body, Environment(env))
            except BreakException: break

    def exec_ForStatement(self, n, env):
        """Handles for-in loops: iterates over lists, strings, dicts, or AuroraRange."""
        it = self.eval(n.iterable, env)
        if isinstance(it, AuroraRange): items = list(range(it.start, it.end+1))
        elif isinstance(it, (list,str)): items = list(it)
        elif isinstance(it, dict): items = list(it.keys())
        else: raise self._err(f"Cannot iterate {self._tname(it)}", n.line)
        for item in items:
            child = Environment(env); child.define(n.variable, item, mutable=True)
            try: self.exec_block(n.body, child)
            except BreakException: break

    def exec_ReturnStatement(self, n, env): raise ReturnException(self.eval(n.value, env) if n.value else None)
    def exec_BreakStatement(self, n, env): raise BreakException()
    def exec_ImportStatement(self, n, env): self.out(f"// module '{n.module_name}' imported")
    def exec_FuncDecl(self, n, env): env.define(n.name, AuroraFunction(n, env), mutable=False)
    def exec_ClassDecl(self, n, env): env.define(n.name, AuroraClass(n.name, n.methods, env), mutable=False)

    # ── Expression evaluators ──────────────────────────────────────────────
    def eval(self, node, env):
        """Dispatches to eval_<NodeType> method."""
        self._track(node)
        fn = getattr(self, f"eval_{type(node).__name__}", None)
        if fn: return fn(node, env)
        raise self._err(f"Unknown expr node: {type(node).__name__}")

    def eval_IntegerLiteral(self,n,e): return n.value
    def eval_FloatLiteral(self,n,e): return n.value
    def eval_StringLiteral(self,n,e): return n.value
    def eval_BoolLiteral(self,n,e): return n.value
    def eval_NullLiteral(self,n,e): return None
    def eval_ListLiteral(self,n,e): return [self.eval(x,e) for x in n.elements]
    def eval_MapLiteral(self,n,e):
        m = {}
        for k,v in n.pairs: m[self._mapkey(self.eval(k,e), n.line)] = self.eval(v,e)
        return m
    def eval_Identifier(self,n,e): return e.get(n.name, n.line)

    def eval_BinaryExpression(self, n, env):
        """Handles binary ops: and/or (short-circuit), arithmetic, comparison, range (..)."""
        op = n.operator; ln = n.line
        if op == "and":
            l = self.eval(n.left, env)
            if not isinstance(l,bool): raise self._err(f"'and' needs Bool, got {self._tname(l)}", ln)
            return l and self.eval(n.right, env)  # short-circuit
        if op == "or":
            l = self.eval(n.left, env)
            if not isinstance(l,bool): raise self._err(f"'or' needs Bool, got {self._tname(l)}", ln)
            return l or self.eval(n.right, env)  # short-circuit
        l = self.eval(n.left, env); r = self.eval(n.right, env)
        if op == "+":
            if isinstance(l,str) and isinstance(r,str): return l+r
            if isinstance(l,(int,float)) and isinstance(r,(int,float)) and not isinstance(l,bool) and not isinstance(r,bool): return l+r
            if isinstance(l,list) and isinstance(r,list): return l+r
            raise self._err(f"Cannot add {self._tname(l)} and {self._tname(r)}", ln)
        if op == "-":
            self._num(l,r,op,ln); return l-r
        if op == "*":
            if isinstance(l,str) and isinstance(r,int) and not isinstance(r,bool): return l*r
            if isinstance(r,str) and isinstance(l,int) and not isinstance(l,bool): return r*l  # Int * String
            self._num(l,r,op,ln); return l*r
        if op == "/":
            self._num(l,r,op,ln)
            if r==0: raise self._err("Division by zero", ln)
            return l//r if isinstance(l,int) and isinstance(r,int) else l/r
        if op == "%":
            self._num(l,r,op,ln)
            if r==0: raise self._err("Modulo by zero", ln)
            return l%r
        if op == "==": return l==r
        if op == "!=": return l!=r
        if op in ("<","<=",">",">="):
            if type(l)!=type(r) and not (isinstance(l,(int,float)) and isinstance(r,(int,float))):
                raise self._err(f"Cannot compare {self._tname(l)} and {self._tname(r)}", ln)
            return {"<":operator.lt, "<=":operator.le, ">":operator.gt, ">=":operator.ge}[op](l, r)
        if op == "..":
            if not isinstance(l,int) or not isinstance(r,int): raise self._err("Range .. needs Int", ln)
            return AuroraRange(l,r)
        raise self._err(f"Unknown operator {op}", ln)

    def _num(self, l, r, op, line=None):
        """Type checking helper for numeric operators (excludes bool)."""
        if not (isinstance(l,(int,float)) and isinstance(r,(int,float)) and not isinstance(l,bool) and not isinstance(r,bool)):
            raise self._err(f"Operator '{op}' needs numbers, got {self._tname(l)} and {self._tname(r)}", line)

    def eval_UnaryExpression(self, n, env):
        """Handles unary - (negation) and not (logical negation)."""
        v = self.eval(n.operand, env)
        if n.operator == "-":
            if not isinstance(v,(int,float)) or isinstance(v,bool): raise self._err(f"Unary - needs number, got {self._tname(v)}", n.line)
            return -v
        if n.operator == "not":
            if not isinstance(v,bool): raise self._err(f"'not' needs Bool, got {self._tname(v)}", n.line)
            return not v

    def eval_CallExpression(self, n, env):
        """Handles function calls: supports user functions, builtins, and class instantiation."""
        callee = self.eval(n.callee, env)
        args   = [self.eval(a, env) for a in n.args]
        # Evaluating the callee and arguments moves current_line into those
        # subtrees, so restore the call site before entering the callee.
        self.current_line = n.line if n.line is not None else self.current_line
        if isinstance(callee, (AuroraFunction, BoundMethod)): return callee.call(args, self, n.line)
        if isinstance(callee, BuiltinFunction): return callee.call(args)
        if isinstance(callee, AuroraClass): return callee.call(args, self, n.line)
        raise self._err(f"Cannot call {self._tname(callee)}", n.line)

    def eval_IndexAccess(self, n, env):
        """Handles indexing: supports lists, dicts, and strings."""
        obj=self.eval(n.obj,env); idx=self.eval(n.index,env)
        if isinstance(obj,list):
            if not isinstance(idx,int) or isinstance(idx,bool): raise self._err("List index must be Int", n.line)
            if idx<0 or idx>=len(obj): raise self._err(f"Index {idx} out of bounds (len={len(obj)})", n.line)
            return obj[idx]
        if isinstance(obj,dict):
            idx = self._mapkey(idx, n.line)
            if idx not in obj: raise self._err(f"Key {idx!r} not in Map", n.line)
            return obj[idx]
        if isinstance(obj,str):
            if not isinstance(idx,int): raise self._err("String index must be Int", n.line)
            if idx<0 or idx>=len(obj): raise self._err(f"Index {idx} out of bounds", n.line)
            return obj[idx]
        raise self._err(f"Cannot index {self._tname(obj)}", n.line)

    def eval_PropertyAccess(self, n, env):
        """Handles property/method access: supports instances and built-in type methods."""
        obj = self.eval(n.obj, env); nm = n.name; ln = n.line
        if isinstance(obj, AuroraInstance): return obj.get(nm, ln)
        if isinstance(obj, list): return self._list_method(obj, nm, ln)
        if isinstance(obj, str): return self._str_method(obj, nm, ln)
        if isinstance(obj, dict): return self._map_method(obj, nm, ln)
        raise self._err(f"No property '{nm}' on {self._tname(obj)}", ln)

    # The closures below outlive this call — they are handed back as
    # BuiltinFunctions and invoked later by eval_CallExpression, with no node in
    # scope. Capturing `line` here is what lets their errors report a location.
    def _list_method(self, lst, nm, line=None):
        """Returns bound methods for List instances (push, pop, len, contains, get)."""
        if nm=="push": return BuiltinFunction("push", lambda a: lst.append(a[0]) or None)
        if nm=="pop": return BuiltinFunction("pop", lambda a: lst.pop() if lst else (_ for _ in ()).throw(self._err("pop on empty list", line)))
        if nm=="len": return BuiltinFunction("len", lambda a: len(lst))
        if nm=="contains": return BuiltinFunction("contains", lambda a: a[0] in lst)
        if nm=="get": return BuiltinFunction("get", lambda a: lst[a[0]])
        raise self._err(f"List has no method '{nm}'", line)

    def _str_method(self, s, nm, line=None):
        """Returns bound methods for String instances (len, upper, lower, contains, split)."""
        if nm=="len": return BuiltinFunction("len", lambda a: len(s))
        if nm=="upper": return BuiltinFunction("upper", lambda a: s.upper())
        if nm=="lower": return BuiltinFunction("lower", lambda a: s.lower())
        if nm=="contains": return BuiltinFunction("contains", lambda a: a[0] in s)
        if nm=="split": return BuiltinFunction("split", lambda a: s.split(a[0] if a else " "))
        raise self._err(f"String has no method '{nm}'", line)

    def _map_method(self, m, nm, line=None):
        """Returns bound methods for Map instances (keys, values, contains, get)."""
        if nm=="keys": return BuiltinFunction("keys", lambda a: list(m.keys()))
        if nm=="values": return BuiltinFunction("values", lambda a: list(m.values()))
        if nm=="contains": return BuiltinFunction("contains", lambda a: self._mapkey(a[0], line) in m)
        if nm=="get": return BuiltinFunction("get", lambda a: m.get(self._mapkey(a[0], line)))
        raise self._err(f"Map has no method '{nm}'", line)