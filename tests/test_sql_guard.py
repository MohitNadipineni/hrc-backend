import pytest

from app.services.sql.guard import UnsafeSQLError, guard_sql

TAX = {"tax"}


def test_simple_select_is_allowed_and_gets_a_limit():
    out = guard_sql("SELECT invoice_id FROM tax.invoices", TAX)
    assert "LIMIT 200" in out


def test_existing_limit_is_kept():
    out = guard_sql("SELECT invoice_id FROM tax.invoices LIMIT 5", TAX)
    assert "LIMIT 5" in out


def test_cte_and_join_are_allowed():
    sql = """
        WITH big AS (SELECT * FROM tax.invoices WHERE total_amount > 50000)
        SELECT v.vendor_name, count(*) FROM big b
        JOIN tax.vendors v ON v.vendor_id = b.vendor_id
        GROUP BY v.vendor_name
    """
    guard_sql(sql, TAX)


@pytest.mark.parametrize("sql", [
    "DELETE FROM tax.invoices",
    "UPDATE tax.invoices SET total_amount = 0",
    "INSERT INTO tax.vendors (vendor_id) VALUES ('X')",
    "DROP TABLE tax.invoices",
    "TRUNCATE tax.invoices",
    "SELECT 1; DROP TABLE tax.invoices",
    "SELECT * INTO tax.copy FROM tax.invoices",
    "SELECT * FROM invoices",
    "SELECT * FROM banking.transactions",
    "SELECT * FROM pg_catalog.pg_user",
    "SELECT pg_sleep(10)",
    "SELECT pg_read_file('/etc/passwd')",
    "GRANT ALL ON tax.invoices TO public",
    "SET ROLE postgres",
    "this is not sql at all",
])
def test_unsafe_sql_is_blocked(sql):
    with pytest.raises(UnsafeSQLError):
        guard_sql(sql, TAX)