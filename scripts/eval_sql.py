import csv

from app.services.sql.cards import build_table_cards
from app.services.sql.runner import run_safe_sql

ALL_GROUPS = ["tax", "banking", "finance"]


def main() -> None:
    cards = build_table_cards({"tax", "banking", "finance"})
    print(f"Built {len(cards)} table cards. Example:\n")
    print(cards["tax.invoices"], "\n")

    with open("data/golden_questions.csv", newline="", encoding="utf-8") as f:
        questions = [q for q in csv.DictReader(f) if q["expected_route"] != "docs"]

    ok = 0
    for q in questions:
        try:
            _, rows = run_safe_sql(q["reference_sql"], ALL_GROUPS)
            ok += 1
            first = rows[0] if rows else "(no rows)"
            print(f"OK    {q['id']} {q['expected_route']:6} {len(rows):3} rows  first: {first}")
        except Exception as e:
            print(f"ERROR {q['id']} {q['expected_route']:6} {type(e).__name__}: {e}")

    print(f"\n{ok}/{len(questions)} reference queries passed the guard and ran read-only")


if __name__ == "__main__":
    main()