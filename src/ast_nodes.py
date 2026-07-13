from dataclasses import dataclass, field
from typing import List, Optional, Any

class ASTNode: 
    """Base class for interpreter's type-based dispatch (eval_XXX/exec_XXX)."""
    pass

@dataclass
class IntegerLiteral(ASTNode): value: int
@dataclass
class FloatLiteral(ASTNode): value: float
@dataclass
class StringLiteral(ASTNode): value: str
@dataclass
class BoolLiteral(ASTNode): value: bool
@dataclass
class NullLiteral(ASTNode): pass
@dataclass
class ListLiteral(ASTNode): elements: List[ASTNode]
@dataclass
class MapLiteral(ASTNode): pairs: list  # (key_node, val_node) tuples
@dataclass
class Identifier(ASTNode): name: str
@dataclass
class IndexAccess(ASTNode): obj: ASTNode; index: ASTNode
@dataclass
class PropertyAccess(ASTNode): obj: ASTNode; name: str
@dataclass
class BinaryExpression(ASTNode): left: ASTNode; operator: str; right: ASTNode
@dataclass
class UnaryExpression(ASTNode): operator: str; operand: ASTNode
@dataclass
class CallExpression(ASTNode): callee: ASTNode; args: List[ASTNode]
@dataclass
class Program(ASTNode): statements: List[ASTNode] = field(default_factory=list)
@dataclass
class VarDecl(ASTNode): type_name: str; name: str; mutable: bool; initializer: ASTNode; line: Optional[int] = None
@dataclass
class AssignStatement(ASTNode): target: ASTNode; value: ASTNode; line: Optional[int] = None
@dataclass
class PrintStatement(ASTNode): expression: ASTNode
@dataclass
class ExprStatement(ASTNode): expression: ASTNode
@dataclass
class IfStatement(ASTNode): condition: ASTNode; then_block: list; else_block: Optional[list]
@dataclass
class WhileStatement(ASTNode): condition: ASTNode; body: list
@dataclass
class ForStatement(ASTNode): variable: str; iterable: ASTNode; body: list
@dataclass
class ReturnStatement(ASTNode): value: Optional[ASTNode]
@dataclass
class BreakStatement(ASTNode): pass
@dataclass
class ImportStatement(ASTNode): module_name: str
@dataclass
class Param(ASTNode): name: str; type_name: Optional[str]
@dataclass
class FuncDecl(ASTNode): name: str; params: list; return_type: Optional[str]; body: list; line: Optional[int] = None
@dataclass
class ClassDecl(ASTNode): name: str; methods: list