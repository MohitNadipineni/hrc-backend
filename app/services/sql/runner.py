from app.core.config import settings
from app.repositories.readonly import run_readonly
from app.services.sql.access import allowed_schemas
from app.services.sql.guard import UnsafeSQLError, guard_sql


def run_safe_sql(sql: str, user_groups: list[str] | None) -> tuple[str, list[dict]]:
    schemas = allowed_schemas(user_groups)
    if not schemas:
        raise UnsafeSQLError("This user has no database access")
    safe_sql = guard_sql(sql, schemas, settings.sql_max_rows)
    return safe_sql, run_readonly(safe_sql)