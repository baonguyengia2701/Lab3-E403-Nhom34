import ast
import operator
from typing import Union

# Safe operators allowed in expressions
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}


def _safe_eval(node) -> Union[int, float]:
    """Recursively evaluate a parsed AST node using only safe operations."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed.")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _ALLOWED_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed.")
        return _ALLOWED_OPERATORS[op_type](_safe_eval(node.operand))
    else:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression string and return the result.

    Args:
        expression: A math expression like "2 + 3 * 4" or "18 / 100 * 1500000"

    Returns:
        The result as a string, or an error message.
    """
    expression = expression.strip()
    # Remove surrounding quotes if the agent wraps the argument
    expression = expression.strip("'\"")
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        # Return clean number: integer if whole, else float
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 6))
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error evaluating expression '{expression}': {e}"


CALCULATOR_TOOL = {
    "name": "calculator",
    "description": (
        "Evaluates a mathematical expression and returns the numeric result. "
        "Supports +, -, *, /, **, %, //. "
        "Input must be a valid math expression string, e.g. '18/100 * 1500000'."
    ),
    "func": calculate,
}
