import csv

from app.agent.thinker import route


def main() -> None:
    with open("data/golden_questions.csv", newline="", encoding="utf-8") as f:
        questions = list(csv.DictReader(f))

    ok = 0
    for q in questions:
        got = route(q["question"])
        right = got == q["expected_route"]
        ok += right
        print(f"{'PASS' if right else 'FAIL'}  {q['id']}  expected {q['expected_route']:6}  got {got:6}  {q['question'][:60]}")

    print(f"\n{ok}/{len(questions)} questions routed correctly")


if __name__ == "__main__":
    main()