import csv
import re
from datetime import datetime
from pathlib import Path

from app.agent.graph import ask
from app.agent.thinker import format_sources
from app.services.sql.runner import run_safe_sql

ALL_GROUPS = ["tax", "banking", "finance", "compliance"]
DOC_ID = re.compile(r"[A-Z]{2,}(?:-[A-Z0-9]+)+")
SKIP_WORDS = {"The", "This", "Within", "And", "Only", "Yes", "No"}


def key_facts(text: str) -> set[str]:
    flat = text.replace(",", "").replace("$", "")
    numbers = set(re.findall(r"\d+(?:\.\d+)?", flat))
    names = {w for w in re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", text) if w not in SKIP_WORDS}
    return numbers | names


def share_found(facts: set[str], text: str) -> float | None:
    if not facts:
        return None
    flat = text.replace(",", "").replace("$", "").lower()
    return sum(1 for f in facts if f.lower() in flat) / len(facts)

def missing(facts: set[str], text: str) -> list[str]:
    flat = text.replace(",", "").replace("$", "").lower()
    return sorted(f for f in facts if f.lower() not in flat)


def rows_key(rows: list[dict]) -> list[tuple]:
    return sorted(tuple(str(v) for v in r.values()) for r in rows)


def show(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "NO"
    return f"{value:.0%}"


def main() -> None:
    with open("data/golden_questions.csv", newline="", encoding="utf-8") as f:
        questions = list(csv.DictReader(f))

    report = []
    for q in questions:
        result = ask(q["question"], ALL_GROUPS)

        route_ok = result["route"] == q["expected_route"]

        expected_docs = DOC_ID.findall(q["expected_sources"])
        cited = [d["doc_id"] for d in result.get("docs", [])]
        source_ok = any(e in cited for e in expected_docs) if expected_docs else None

        facts = key_facts(q["expected_answer"])
        evidence = format_sources(result.get("docs", []), result.get("sql"), result.get("rows"))
        facts_evidence = share_found(facts, evidence)
        facts_answer = share_found(facts, result["answer"])

        rows_ok = None
        if q["reference_sql"].strip():
            _, ref_rows = run_safe_sql(q["reference_sql"], ALL_GROUPS)
            got = result.get("rows")
            rows_ok = got is not None and rows_key(got) == rows_key(ref_rows)

        row = {"id": q["id"], "expected_route": q["expected_route"], "got_route": result["route"],
               "route_ok": show(route_ok), "source_ok": show(source_ok),
               "facts_in_evidence": show(facts_evidence), "facts_in_answer": show(facts_answer),
               "rows_ok": show(rows_ok), "warnings": "; ".join(result.get("warnings", []))}
        report.append(row)
        print(f"{row['id']}  route {row['route_ok']:3}  source {row['source_ok']:3}  "
              f"facts: evidence {row['facts_in_evidence']:>4}  answer {row['facts_in_answer']:>4}  "
              f"rows {row['rows_ok']:3}  {q['question'][:45]}")
        gaps = missing(facts, evidence)
        if gaps:
            print("      missing from evidence:", ", ".join(gaps))

    def score(col: str) -> str:
        marks = [r[col] for r in report if r[col] != "n/a"]
        return f"{sum(m == 'yes' for m in marks)}/{len(marks)}"

    def average(col: str) -> str:
        values = [int(r[col].rstrip("%")) for r in report if r[col] != "n/a"]
        return f"{sum(values) / len(values):.0f}%" if values else "n/a"

    print(f"\nRoute correct:          {score('route_ok')}")
    print(f"Right document found:   {score('source_ok')}")
    print(f"SQL rows match:         {score('rows_ok')}")
    print(f"Key facts in evidence:  {average('facts_in_evidence')} on average")
    print(f"Key facts in answer:    {average('facts_in_answer')} on average")

    Path("reports").mkdir(exist_ok=True)
    out = Path("reports") / f"eval_{datetime.now():%Y%m%d_%H%M}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(report[0]))
        writer.writeheader()
        writer.writerows(report)
    print(f"\nReport saved to {out}")


if __name__ == "__main__":
    main()