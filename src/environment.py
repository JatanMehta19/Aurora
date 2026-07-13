class AuroraRuntimeError(Exception):
    def __init__(self, msg, line=None):
        prefix = f"[Line {line}] " if line else ""
        super().__init__(f"{prefix}Runtime Error: {msg}")

class Environment:
    def __init__(self, parent=None, type_checker=None):
        self.vars = {}  # name -> {value, mutable, type}
        self.parent = parent
        # Validates a value against a declared type name. Inherited from the parent
        # scope so every environment ultimately shares the interpreter's checker.
        self.type_checker = type_checker if type_checker is not None else (parent.type_checker if parent else None)

    def define(self, name, value, mutable=True, type_name=None):
        self.vars[name] = {"value": value, "mutable": mutable, "type": type_name}

    def get(self, name):
        if name in self.vars: return self.vars[name]["value"]
        if self.parent: return self.parent.get(name)
        raise AuroraRuntimeError(f"Undefined variable '{name}'")

    def assign(self, name, value, line=None):
        if name in self.vars:
            if not self.vars[name]["mutable"]:
                raise AuroraRuntimeError(f"Cannot reassign immutable variable '{name}'", line)
            declared = self.vars[name]["type"]
            if declared and self.type_checker:  # enforce the declared type on reassignment
                self.type_checker(declared, value, name, line)
            self.vars[name]["value"] = value
            return
        if self.parent:
            self.parent.assign(name, value, line)
            return
        raise AuroraRuntimeError(f"Undefined variable '{name}'", line)
