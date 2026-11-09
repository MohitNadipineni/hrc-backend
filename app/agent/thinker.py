import csv
import re

from app.clients.llm import chat
from app.core.config import settings


def _offline() -> bool:
    return settings.llm_provider == "offline"


# ---------- Job 1: decide where to look ----------

ROUTE_PROMPT = """You decide where to look to answer a finance question.
Reply with exactly one word:
docs   - the answer is in company documents (policies, procedures, letters, memos, slides)
sql    - the answer needs counting or listing rows in the database (invoices, transactions, loans, budgets, tax payments)
hybrid - it needs a rule from a document AND data from the database"""

DATA_WORDS = {"list", "highest", "top", "count", "average", "invoices", "deposits", "loans",
              "transactions", "spend", "balance", "customers", "vendors", "lines", "paid"}
DATA_PHRASES = ("how much", "how many")
DOC_WORDS = {"policy", "rule", "rules", "sop", "deadline", "approval", "required", "requirement",
             "say", "guidance", "why", "procedure", "notice", "memo", "committee", "thresholds", "graded"}


def route(question: str) -> str:
    if _offline():
        return _route_offline(question)
    answer = chat(ROUTE_PROMPT, question).strip().lower()
    return answer if answer in {"docs", "sql", "hybrid"} else "hybrid"


def _route_offline(question: str) -> str:
    q = question.lower()
    words = set(re.findall(r"[a-z0-9&-]+", q))
    needs_data = bool(words & DATA_WORDS) or any(p in q for p in DATA_PHRASES)
    needs_docs = bool(words & DOC_WORDS)
    if needs_data and needs_docs:
        return "hybrid"
    if needs_data:
        return "sql"
    return "docs"


# ---------- Job 2: write SQL ----------

SQL_PROMPT = """You write one PostgreSQL SELECT query to answer the question.
Rules:
- Use only the tables and columns in the table cards below. Always write schema.table, e.g. tax.invoices.
- One SELECT statement only. Never change data.
- Give every calculated column a clear name with AS.
- Apply any rules from the document excerpts (limits, dates, periods) when they are relevant.
- Reply with the SQL only: no explanation, no ``` marks.

Table cards:
{cards}

Document excerpts:
{docs}"""


def write_sql(question: str, cards: dict[str, str], doc_context: str, error: str = "") -> str | None:
    if _offline():
        golden = _golden_sql()
        q = _norm(question)
        if q in golden:
            return golden[q]
        for known, sql in golden.items():
            if q.startswith(known):
                return sql
        return None
    system = SQL_PROMPT.replace("{cards}", "\n\n".join(cards.values())).replace("{docs}", doc_context or "(none)")
    user = question if not error else f"{question}\n\nYour previous SQL failed with: {error}\nWrite a corrected query."
    sql = chat(system, user).strip().strip("`").strip()
    return sql.removeprefix("sql").strip()


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _golden_sql() -> dict[str, str]:
    with open("data/golden_questions.csv", newline="", encoding="utf-8") as f:
        return {_norm(q["question"]): q["reference_sql"]
                for q in csv.DictReader(f) if q["reference_sql"].strip()}


# ---------- Job 3: write the answer ----------

ANSWER_PROMPT = """You answer finance questions using ONLY the numbered sources below.
- After every fact, add its source tag in square brackets, e.g. [D1] or [S1].
- If the sources do not contain the answer, say so plainly. Never guess.
- Start with a short direct answer, then the key details as bullet points."""

def _row_text(row: dict) -> str:
    return ", ".join(f"{k}: {v}" for k, v in row.items())
def format_sources(docs: list[dict], sql: str | None, rows: list[dict] | None) -> str:
    parts = [f"[D{i}] {d['doc_id']} ({d['section']}):\n{d['content']}" for i, d in enumerate(docs, 1)]
    if rows is not None:
        shown = "\n".join(_row_text(r) for r in rows[:30]) or "(no rows)"
        parts.append(f"[S1] Database query:\n{sql}\nResult rows:\n{shown}")
    return "\n\n".join(parts)


def write_answer(question: str, docs: list[dict], sql: str | None, rows: list[dict] | None) -> str:
    if _offline():
        return _answer_offline(docs, rows)
    sources = format_sources(docs, sql, rows)
    return chat(ANSWER_PROMPT, f"Question: {question}\n\nSources:\n{sources}")


def _answer_offline(docs: list[dict], rows: list[dict] | None) -> str:
    lines = ["(Offline stand-in: this lists the evidence found instead of writing a real answer.)"]
    for i, d in enumerate(docs, 1):
        body = d["content"].split("\n\n", 1)[-1].replace("\n", " ")
        lines.append(f"- {d['doc_id']}, {d['section']}: {body[:400]}... [D{i}]")
    if rows is not None:
        lines.append(f"- The database query returned {len(rows)} row(s) [S1]:")
        for r in rows[:10]:
                        lines.append("    " + _row_text(r))
    if len(lines) == 1:
        lines.append("I could not find anything to answer this.")
    return "\n".join(lines)

# ---------- Job 4: make a follow-up question stand on its own ----------

CONDENSE_PROMPT = """Rewrite the user's latest question so it can be understood on its own,
using the conversation so far. Keep all names, numbers, dates and document IDs.
Reply with the rewritten question only."""

FOLLOW_UP_WORDS = {"it", "its", "that", "this", "those", "these", "they", "them", "more", "else"}


def _looks_like_follow_up(question: str) -> bool:
    words = re.findall(r"[a-z']+", question.lower())
    return len(words) <= 5 or bool(set(words) & FOLLOW_UP_WORDS)


def condense(question: str, history: list[dict]) -> str:
    previous = [m["content"] for m in history if m["role"] == "user"]
    if not previous:
        return question
    if _offline():
        return f"{previous[-1]} {question}" if _looks_like_follow_up(question) else question
    convo = "\n".join(f"{m['role']}: {m['content'][:500]}" for m in history[-6:])
    return chat(CONDENSE_PROMPT, f"Conversation so far:\n{convo}\n\nLatest question: {question}").strip()