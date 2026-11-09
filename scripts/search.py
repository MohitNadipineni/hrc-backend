import sys

from app.services.retrieval import search

question = " ".join(sys.argv[1:]) or "When do exemption certificates expire?"
print(f"Q: {question}\n")
for i, r in enumerate(search(question), 1):
    print(f"{i}. {r['doc_id']} | {r['content_type']} | {r['section']} "
          f"| overlap={r['overlap']:.2f} rrf={r['rrf']:.4f}")
    body = r["content"].split("\n\n", 1)[-1]
    print("   ", body[:160].replace("\n", " "), "\n")