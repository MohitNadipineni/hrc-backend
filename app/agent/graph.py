import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent import thinker
from app.services.retrieval import search
from app.services.sql.access import allowed_schemas
from app.services.sql.cards import build_table_cards
from app.services.sql.runner import run_safe_sql


class AgentState(TypedDict, total=False):
    question: str
    user_groups: list[str]
    route: str
    docs: list[dict]
    cards: dict[str, str]
    sql: str | None
    rows: list[dict] | None
    sql_error: str
    answer: str
    warnings: list[str]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


# ---------- the steps (nodes) ----------

def decide_route(state: AgentState) -> dict:
    return {"route": thinker.route(state["question"])}


def search_docs(state: AgentState) -> dict:
    return {"docs": search(state["question"], user_groups=state.get("user_groups"), top_k=5)}


def pick_tables(state: AgentState) -> dict:
    schemas = allowed_schemas(state.get("user_groups"))
    cards = build_table_cards(schemas) if schemas else {}
    q = _words(state["question"])
    ranked = sorted(cards, key=lambda name: len(q & _words(cards[name])), reverse=True)
    return {"cards": {name: cards[name] for name in ranked[:4]}}


def run_sql(state: AgentState) -> dict:
    doc_context = "\n\n".join(d["content"] for d in state.get("docs", [])[:3])
    error, sql = "", None
    for _attempt in range(2):
        sql = thinker.write_sql(state["question"], state.get("cards", {}), doc_context, error)
        if not sql:
            return {"sql": None, "rows": None, "sql_error": "No SQL could be written for this question."}
        try:
            safe_sql, rows = run_safe_sql(sql, state.get("user_groups"))
            return {"sql": safe_sql, "rows": rows, "sql_error": ""}
        except Exception as e:
            error = str(e)
    return {"sql": sql, "rows": None, "sql_error": error}


def write_answer(state: AgentState) -> dict:
    answer = thinker.write_answer(state["question"], state.get("docs", []),
                                  state.get("sql"), state.get("rows"))
    return {"answer": answer}


def check_grounding(state: AgentState) -> dict:
    answer = state.get("answer", "")
    n_docs = len(state.get("docs", []))
    has_sql = state.get("rows") is not None
    warnings = []

    tags = re.findall(r"\[(D|S)(\d+)\]", answer)
    if not tags:
        warnings.append("The answer has no citations, so it cannot be checked against the sources.")
    for kind, num in tags:
        n = int(num)
        if kind == "D" and not 1 <= n <= n_docs:
            warnings.append(f"[D{n}] does not match any document that was found.")
        if kind == "S" and not (has_sql and n == 1):
            warnings.append(f"[S{n}] does not match any query that was run.")
    if state.get("sql_error"):
        warnings.append(f"Database step failed: {state['sql_error']}")

    return {"warnings": sorted(set(warnings))}


# ---------- the flowchart (edges) ----------

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("decide_route", decide_route)
    g.add_node("search_docs", search_docs)
    g.add_node("pick_tables", pick_tables)
    g.add_node("run_sql", run_sql)
    g.add_node("write_answer", write_answer)
    g.add_node("check_grounding", check_grounding)

    g.add_edge(START, "decide_route")
    g.add_conditional_edges(
        "decide_route",
        lambda s: "pick_tables" if s["route"] == "sql" else "search_docs",
        ["pick_tables", "search_docs"],
    )
    g.add_conditional_edges(
        "search_docs",
        lambda s: "pick_tables" if s["route"] == "hybrid" else "write_answer",
        ["pick_tables", "write_answer"],
    )
    g.add_edge("pick_tables", "run_sql")
    g.add_edge("run_sql", "write_answer")
    g.add_edge("write_answer", "check_grounding")
    g.add_edge("check_grounding", END)
    return g.compile()


agent = build_graph()


def ask(question: str, user_groups: list[str] | None = None) -> dict:
    return agent.invoke({"question": question, "user_groups": user_groups or []})