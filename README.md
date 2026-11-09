# HRC Backend: Hybrid RAG Finance Chatbot

A backend for a chatbot that answers finance, tax and banking questions by **looking things up before answering**. It searches company documents (the rules) and queries a database (the facts), then answers with citations showing where every fact came from: `[D1]` for a document, `[S1]` for a database query.

> **Status:** Days 1–7, 9 and 10 of the 10-day plan are complete. The project currently runs in **offline mode** (stand-in AI) until an Azure OpenAI key is added. Day 8 (the ReAct agent) is postponed until then. See [Current status](#current-status).

---

## What it does

- **Hybrid sources.** Some questions need documents, some need the database, the hardest need both. A question like *"Which 2026 invoices over $50,000 violate the exemption certificate policy?"* reads the rule from the policy, then counts the matching invoices.
- **Hybrid search.** Documents are searched two ways at once, by keywords and by meaning, merged with RRF, filtered by a relevance threshold and reranked.
- **Safe SQL.** AI-written SQL passes three locks: a `sqlglot` guard, a read-only database user, and a read-only transaction.
- **Permissions.** Restricted documents and database schemas are only visible to the right groups.
- **Conversations.** Follow-up questions use the earlier conversation. Each user sees only their own conversations.
- **Grounding check.** Every citation in an answer is checked against what was actually found.

## How a question flows

```
question → decide route ──┬── docs ────→ search documents ───────────────────────→ write answer → check citations
                          ├── sql ─────────────────────────→ pick tables → run SQL ─┘
                          └── hybrid ─→ search documents ─→ pick tables → run SQL ─┘
```

For hybrid questions, documents are searched first so rules found there (a limit, an audit period) can shape the SQL. The flow is built with LangGraph in `app/agent/graph.py`.

## Tech stack

| Tool | Job |
| --- | --- |
| Python 3.12 | Language |
| FastAPI + Uvicorn | Web API and server |
| Pydantic / pydantic-settings | Request/response shapes and settings |
| LangGraph | The agent's step-by-step flow |
| LangChain (langchain-openai) | Calls to Azure OpenAI (GPT-4o and text-embedding-3-large) |
| PostgreSQL 16 + pgvector | The database, plus vector and full-text search |
| psycopg 3 | Python ↔ Postgres |
| sqlglot | Inspects AI-written SQL before it runs |
| python-docx, pdfplumber, python-pptx | Read Word, PDF and PowerPoint files |
| Docker + Docker Compose | Run the database and app together |
| pytest | Tests |

---

## Quick start (Docker)

You need **Docker Desktop**, running.

```bash
docker compose up --build -d
```

This starts two containers:

- **db**: PostgreSQL 16 with pgvector. On its very first start it creates the tables and loads the sample data.
- **app**: the API on <http://localhost:8000>. On every start it makes sure the `chunks` and `app` tables exist, and ingests the documents if none are stored yet.

Check it:

```bash
docker compose ps                 # db should be (healthy), app should be Up
docker compose logs app           # startup messages
curl http://localhost:8000/readyz # {"status":"ready", ...}
```

Interactive API docs: <http://localhost:8000/docs>

Stop everything (data is kept):

```bash
docker compose down
```

> ⚠️ `docker compose down -v` also **deletes the database volume**. Only use it to start completely fresh.

## Local development (without the app container)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d db                      # database only
python -m scripts.setup_db                   # create tables, ingest if empty
uvicorn app.main:app --reload                # API on http://127.0.0.1:8000
```

---

## Configuration

Settings live in `.env` (never committed) and are read by `app/core/config.py`.

| Setting | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/ragdemo` | Full-access connection for the app's own work |
| `DATABASE_RO_URL` | `postgresql://chatbot_ro:change-me@localhost:5432/ragdemo` | Read-only connection used for AI-written SQL |
| `LLM_PROVIDER` | `offline` | `offline` (stand-in) or `azure` (real models) |
| `EMBEDDING_DIM` | `1536` | Length of each embedding. Must match `vector(1536)` in `chunks.sql` |
| `SHAREPOINT_DIR` | `data/sharepoint` | Folder holding the source documents |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | — | Azure OpenAI key |
| `AZURE_OPENAI_API_VERSION` | `2024-10-21` | API version |
| `AZURE_EMBEDDING_DEPLOYMENT` | — | Deployment name of the embedding model |
| `AZURE_CHAT_DEPLOYMENT` | — | Deployment name of GPT-4o |
| `CANDIDATE_K` | `20` | Results fetched by each search before merging |
| `MIN_SIMILARITY` | `0.30` | Relevance threshold for meaning-only matches |
| `SQL_MAX_ROWS` | `200` | Row limit the guard adds to queries |
| `SQL_TIMEOUT_MS` | `5000` | Time limit for each query |
| `AUTH_MODE` | `dev` | `dev` (identity from headers) or `apikey` |
| `API_KEYS` | `{}` | JSON: `{"<key>": {"user_id": "...", "groups": ["tax"]}}` |

Inside Docker, `docker-compose.yml` overrides the two database URLs to use the host `db` instead of `localhost`.

---

## API

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/healthz` | Is the app running? |
| `GET` | `/readyz` | Can it reach the database? (503 if not) |
| `POST` | `/v1/chat` | Ask a question. Optional `thread_id` continues a conversation |
| `POST` | `/v1/chat/stream` | Same, streamed as Server-Sent Events: `meta`, many `token`, then `done` |
| `GET` | `/v1/threads` | List my conversations |
| `GET` | `/v1/threads/{thread_id}` | Read one of my conversations |
| `DELETE` | `/v1/threads/{thread_id}` | Delete one of my conversations |
| `POST` | `/v1/feedback` | Thumbs up (`1`) or down (`-1`) on one of my answers |

Example:

```bash
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-Id: demo" \
  -d '{"question": "What is the deadline to file a SAR?"}'
```

The response includes `answer`, `route` (`docs` / `sql` / `hybrid`), `citations`, the `sql` used, `warnings`, `thread_id`, `message_id` and the `standalone_question` actually searched.

### Logins

- **`dev` mode** (default, for building and testing): send `X-User-Id` and, optionally, `X-User-Groups: tax,finance`. With no groups header you get all groups. Not secure.
- **`apikey` mode**: send `X-API-Key`. The user and groups come only from `API_KEYS` in settings, and any `X-User-Groups` header is ignored. Missing or wrong keys get `401`.

### Permissions

| Group | Database schemas | Restricted documents |
| --- | --- | --- |
| `tax` | `tax` | — |
| `banking` | `banking` | — |
| `compliance` | `banking` | `AML-SOP-021` |
| `finance` | `finance` | — |

Document restrictions live in `DOC_GROUPS` in `scripts/ingest.py`; schema access lives in `app/services/sql/access.py`.

---

## Testing and evaluation

```bash
python -m pytest -q            # 57 tests; database tests are skipped if Docker is off
python -m scripts.run_eval     # grades all 16 golden questions, saves reports/eval_<date>.csv
```

The tests include the three key safety tests:

1. A user without the right group cannot see a restricted document.
2. AI-written SQL that tries to change data is blocked (by the guard, and by the read-only session even without the guard).
3. One user cannot read, continue, delete or rate another user's conversation.

The evaluation checks, for each golden question: the route, whether the expected document was found, whether the key facts appear in the evidence and in the answer, and whether the SQL rows match the reference.

**Offline baseline** (`reports/eval_20261109_2342.csv`):

| Check | Result |
| --- | --- |
| Route correct | 16/16 |
| Right document found | 12/12 |
| SQL rows match | 10/10 (replayed reference SQL, see below) |
| Key facts in evidence | 100% |
| Key facts in answer | 98% |

Other useful scripts:

| Script | Purpose |
| --- | --- |
| `scripts/ingest.py` | Read, chunk, embed and store the documents |
| `scripts/search.py "question"` | Show the top 5 search results |
| `scripts/ask.py "question"` | Run the full agent from the terminal |
| `scripts/demo.py` | Walk through the key features against the running API |
| `scripts/setup_db.py` | Create the extra tables; ingest if empty |

---

## Project layout

```
app/
  main.py                   creates the app, plugs in routers
  core/config.py            settings
  core/auth.py              dev and API-key logins
  api/routers/health.py     /healthz, /readyz
  api/routers/chat.py       chat, streaming, threads, feedback
  schemas/chat.py           request and response shapes
  agent/thinker.py          route / write SQL / write answer / condense (real AI or stand-in)
  agent/graph.py            the LangGraph flow and grounding check
  services/chat.py          conversations + agent
  services/retrieval.py     hybrid search, RRF, threshold, reranker
  services/ingestion/       document loaders and chunker
  services/sql/             guard, access, table cards, safe runner
  clients/embeddings.py     embeddings (real or stand-in)
  clients/llm.py            chat model calls
  repositories/             all SQL: chunks, threads, read-only runner, catalog
scripts/                    ingestion, setup, evaluation and demo scripts
tests/                      unit tests + integration tests (tests/integration)
data/                       documents, database schema and seed, golden questions
deploy/                     database setup SQL and role script
```

---

## Current status

**Working now (offline mode):** ingestion, hybrid search with permissions, the SQL safety system, the LangGraph agent with citations and grounding check, the full API with conversations, streaming, feedback and logins, 57 passing tests, the evaluation, and Docker.

**Offline mode** uses stand-ins so everything runs without an AI key:

- Embeddings are hash-based, so they have no real meaning. Keyword search carries the search.
- Routing uses keyword rules, tuned on the 16 golden questions.
- SQL writing **replays the reference SQL** for the 16 golden questions only; other database questions get an honest "could not write SQL" warning.
- Answers list the evidence found rather than being written as prose.

**To switch to the real models:**

1. In `.env`, set `LLM_PROVIDER=azure` and fill in the five `AZURE_...` settings.
2. Re-embed the documents with the real model: `python -m scripts.ingest`
3. Restart the app: `docker compose up --build -d`
4. Run `python -m scripts.run_eval` and compare with the offline baseline.

**Still to do:**

- Day 8: the ReAct agent (needs the real AI).
- Stream tokens as the AI writes them (currently the finished answer is streamed word by word).
- Real logins (Entra ID), live SharePoint, and LangSmith tracing, if required.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `Cannot connect to the Docker daemon` | Open Docker Desktop and wait for "Engine running" |
| `ModuleNotFoundError: No module named 'app...'` | Run commands from the project folder, with `.venv` activated; check the file is in the right folder |
| `/readyz` says ready with the database stopped | Another Postgres is using port 5432: find it with `docker ps` and stop it |
| `zsh: parse error` | Only the command was meant to be pasted, not the terminal prompt before it |
| Port 8000 already in use | Stop any local `uvicorn` (Ctrl + C) before `docker compose up` |
