import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


class UnsafeSQLError(ValueError):
    """Raised when AI-written SQL is not a single safe SELECT."""


_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "AlterTable",
    "TruncateTable", "Command", "Into", "Grant", "Revoke", "Copy", "Set",
    "Transaction", "Commit", "Rollback", "Lock",
]
FORBIDDEN = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

QUERY_TYPES = tuple(getattr(exp, n) for n in ["Select", "Union", "Intersect", "Except"] if hasattr(exp, n))

BLOCKED_FUNCTIONS = {"dblink", "lo_import", "lo_export", "set_config"}


def guard_sql(sql: str, allowed_schemas: set[str], max_rows: int = 200) -> str:
    # 1. It must be valid SQL.
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except ParseError as e:
        raise UnsafeSQLError(f"SQL could not be parsed: {e}") from e

    # 2. Exactly one statement.
    if len(statements) != 1:
        raise UnsafeSQLError(f"Expected exactly 1 statement, got {len(statements)}")
    tree = statements[0]

    # 3. It must be a query (SELECT, or SELECTs joined with UNION and friends).
    if not isinstance(tree, QUERY_TYPES):
        raise UnsafeSQLError(f"Only SELECT queries are allowed, got {tree.key.upper()}")

    # 4. Nothing anywhere inside it may change data or settings.
    for node in tree.walk():
        if isinstance(node, FORBIDDEN):
            raise UnsafeSQLError(f"Forbidden operation: {node.key.upper()}")

    # 5. No dangerous functions.
    for fn in tree.find_all(exp.Anonymous):
        name = fn.name.lower()
        if name.startswith("pg_") or name in BLOCKED_FUNCTIONS:
            raise UnsafeSQLError(f"Function not allowed: {name}")

    # 6. Every table must be schema-qualified and in an allowed schema.
    cte_names = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        if not table.db and table.name in cte_names:
            continue
        if not table.db:
            raise UnsafeSQLError(f"Table '{table.name}' must include its schema, e.g. tax.{table.name}")
        if table.db not in allowed_schemas:
            raise UnsafeSQLError(f"Schema '{table.db}' is not allowed for this user")

    # 7. Cap the number of rows.
    if not tree.args.get("limit"):
        tree = tree.limit(max_rows)

    return tree.sql(dialect="postgres")