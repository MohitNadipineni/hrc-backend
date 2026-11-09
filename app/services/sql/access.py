GROUP_SCHEMAS = {
    "tax": {"tax"},
    "banking": {"banking"},
    "compliance": {"banking"},
    "finance": {"finance"},
}


def allowed_schemas(user_groups: list[str] | None) -> set[str]:
    schemas: set[str] = set()
    for group in user_groups or []:
        schemas |= GROUP_SCHEMAS.get(group, set())
    return schemas