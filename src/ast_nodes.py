from dataclasses import dataclass, field
from typing import List, Optional, Any

class ASTNode:
    """Base class for interpreter's type-based dispatch (eval_XXX/exec_XXX)."""
    pass

# Every dispatched node carries a source ``line``. It is the last field and
# defaults to None so positional construction stays valid, and so the
# interpreter can always reach for it via getattr(node, "line", None).
# Program and Param are omitted: neither is ever passed to exec()/eval().

@dataclass
class IntegerLiteral(ASTNode): value: int; line: Optional[int] = None
@dataclass
class FloatLiteral(ASTNode): value: float; line: Optional[int] = None
@dataclass
class StringLiteral(ASTNode): value: str; line: Optional[int] = None
@dataclass
class BoolLiteral(ASTNode): value: bool; line: Optional[int] = None
@dataclass
class NullLiteral(ASTNode): line: Optional[int] = None
@dataclass
class ListLiteral(ASTNode): elements: List[ASTNode]; line: Optional[int] = None
@dataclass
class MapLiteral(ASTNode): pairs: list; line: Optional[int] = None  # (key_node, val_node) tuples
@dataclass
class Identifier(ASTNode): name: str; line: Optional[int] = None
@dataclass
class IndexAccess(ASTNode): obj: ASTNode; index: ASTNode; line: Optional[int] = None
@dataclass
class PropertyAccess(ASTNode): obj: ASTNode; name: str; line: Optional[int] = None
@dataclass
class BinaryExpression(ASTNode): left: ASTNode; operator: str; right: ASTNode; line: Optional[int] = None
@dataclass
class UnaryExpression(ASTNode): operator: str; operand: ASTNode; line: Optional[int] = None
@dataclass
class CallExpression(ASTNode): callee: ASTNode; args: List[ASTNode]; line: Optional[int] = None
@dataclass
class Program(ASTNode): statements: List[ASTNode] = field(default_factory=list)
@dataclass
class VarDecl(ASTNode): type_name: str; name: str; mutable: bool; initializer: ASTNode; line: Optional[int] = None
@dataclass
class AssignStatement(ASTNode): target: ASTNode; value: ASTNode; line: Optional[int] = None
@dataclass
class PrintStatement(ASTNode): expression: ASTNode; line: Optional[int] = None
@dataclass
class ExprStatement(ASTNode): expression: ASTNode; line: Optional[int] = None
@dataclass
class IfStatement(ASTNode): condition: ASTNode; then_block: list; else_block: Optional[list]; line: Optional[int] = None
@dataclass
class WhileStatement(ASTNode): condition: ASTNode; body: list; line: Optional[int] = None
@dataclass
class ForStatement(ASTNode): variable: str; iterable: ASTNode; body: list; line: Optional[int] = None
@dataclass
class ReturnStatement(ASTNode): value: Optional[ASTNode]; line: Optional[int] = None
@dataclass
class BreakStatement(ASTNode): line: Optional[int] = None
@dataclass
class ImportStatement(ASTNode): module_name: str; line: Optional[int] = None
@dataclass
class Param(ASTNode): name: str; type_name: Optional[str]
@dataclass
class FuncDecl(ASTNode): name: str; params: list; return_type: Optional[str]; body: list; line: Optional[int] = None
@dataclass
class ClassDecl(ASTNode): name: str; methods: list; line: Optional[int] = None
