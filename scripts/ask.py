import sys

from app.agent.graph import ask

DEFAULT = ("Are there Ohio invoices in the audit period with the same certificate problem "
           "that the notice did not cite? What extra tax would we owe?")

question = " ".join(sys.argv[1:]) or DEFAULT
result = ask(question, user_groups=["tax", "banking", "finance", "compliance"])

print("Q:", question)
print("Route:", result["route"])
if result.get("sql"):
    print("SQL used [S1]:", result["sql"])
print("\nAnswer:\n" + result["answer"])
print("\nWarnings:", result.get("warnings") or "none")