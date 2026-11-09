import csv
import re

from app.services.retrieval import search

EVAL_GROUPS = ["compliance", "tax", "finance", "banking"]


def main() -> None:
    with open("data/golden_questions.csv", newline="", encoding="utf-8") as f:
        questions = [q for q in csv.DictReader(f) if q["expected_route"] == "docs"]

    passed = 0
    for q in questions:
        expected = [s.strip() for s in re.split(r"[;|,]", q["expected_sources"]) if s.strip()]
        results = search(q["question"], user_groups=EVAL_GROUPS, top_k=3)
        found = [r["doc_id"] for r in results]
        ok = any(e in found for e in expected)
        passed += ok
        mark = "PASS" if ok else "FAIL"
        print(f"{mark}  {q['id']}  expected {expected}  got {found}")
        print(f"      {q['question']}")

    print(f"\n{passed}/{len(questions)} document questions found the right document in the top 3")


if __name__ == "__main__":
    main()