from app.repositories.catalog import fetch_columns


def build_table_cards(schemas: set[str]) -> dict[str, str]:
    tables: dict[str, dict] = {}
    for r in fetch_columns(sorted(schemas)):
        name = f"{r['table_schema']}.{r['table_name']}"
        t = tables.setdefault(name, {"comment": r["table_comment"] or "", "columns": []})
        note = f"  -- {r['column_comment']}" if r["column_comment"] else ""
        t["columns"].append(f"  {r['column_name']} ({r['data_type']}){note}")

    return {name: f"Table {name}: {t['comment']}\n" + "\n".join(t["columns"])
            for name, t in tables.items()}