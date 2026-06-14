"""Safe arithmetic-expression evaluation for amounts.

Amounts everywhere (income, transactions, budgets) may be typed as expressions
like ``15.71+1.35`` or ``(7.81)/2+6.5`` (docs/DEVELOPING.md). We parse with
``ast`` and walk only a tiny whitelist of nodes — ``+ - * /``, parentheses, and
unary ``+/-`` over numeric literals — so no name, call, attribute, power, or
other construct can ever execute. Numbers are read from their **source text**
(not the parsed float) so ``1.35`` stays exact, and the whole expression is
evaluated in full Decimal precision then quantized once into 4dp ``Money``.
"""

from __future__ import annotations

import ast
import operator
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Callable

from .errors import ExpressionError
from .money import Money

_MAX_LEN = 200

_BINOPS: dict[type, Callable[[Decimal, Decimal], Decimal]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def evaluate(expr: str) -> Money:
    """Safely evaluate an arithmetic amount expression to 4dp ``Money``.

    Raises :class:`ExpressionError` on anything outside the whitelist
    (names, calls, attributes, power, comparisons, …), on syntax errors,
    and on division by zero.
    """
    if not isinstance(expr, str):
        raise ExpressionError(
            f"expression must be a string, got {type(expr).__name__}"
        )
    text = expr.strip()
    if not text:
        raise ExpressionError("empty expression")
    if len(text) > _MAX_LEN:
        raise ExpressionError("expression too long")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"invalid expression: {expr!r}") from exc
    return Money(_eval(tree.body, text))


def _eval(node: ast.AST, src: str) -> Decimal:
    if isinstance(node, ast.Constant):
        return _number(node, src)
    if isinstance(node, ast.UnaryOp):
        operand = _eval(node.operand, src)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ExpressionError("unsupported unary operator")
    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise ExpressionError("unsupported operator")
        left = _eval(node.left, src)
        right = _eval(node.right, src)
        try:
            return op(left, right)
        except (DivisionByZero, ZeroDivisionError, InvalidOperation) as exc:
            raise ExpressionError("division by zero") from exc
    raise ExpressionError("unsupported syntax in expression")


def _number(node: ast.Constant, src: str) -> Decimal:
    if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
        raise ExpressionError("only numeric literals are allowed")
    segment = ast.get_source_segment(src, node)
    text = (segment if segment is not None else repr(node.value)).replace("_", "")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ExpressionError(f"invalid number: {text!r}") from exc