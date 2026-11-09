from app.agent import thinker
from app.agent.graph import ask
from app.core.auth import User
from app.repositories import threads


class ThreadNotFound(Exception):
    """Raised when a thread does not exist or belongs to someone else."""


def build_citations(result: dict) -> list[dict]:
    citations = [{"tag": f"D{i}", "source": d["doc_id"], "detail": d["section"] or ""}
                 for i, d in enumerate(result.get("docs", []), 1)]
    if result.get("rows") is not None:
        citations.append({"tag": "S1", "source": "database query", "detail": result["sql"]})
    return citations


def handle_chat(user: User, question: str, thread_id: str | None) -> dict:
    if thread_id:
        if threads.get_thread(thread_id, user.user_id) is None:
            raise ThreadNotFound()
        history = threads.get_messages(thread_id)
    else:
        thread_id = threads.create_thread(user.user_id, question[:80])
        history = []

    standalone = thinker.condense(question, history)
    result = ask(standalone, user.groups)

    details = {
        "route": result["route"],
        "citations": build_citations(result),
        "sql": result.get("sql") if result.get("rows") is not None else None,
        "warnings": result.get("warnings", []),
        "standalone_question": standalone,
    }
    threads.add_message(thread_id, "user", question)
    message_id = threads.add_message(thread_id, "assistant", result["answer"], details)

    return {"thread_id": thread_id, "message_id": message_id, "answer": result["answer"], **details}