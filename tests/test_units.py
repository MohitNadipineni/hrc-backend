import csv

import pytest

from app.agent.thinker import _route_offline
from app.services.ingestion.chunker import _split, add_header, chunk_blocks
from app.services.ingestion.loaders import Block
from app.services.retrieval import _overlap, _rrf, _terms


def golden() -> list[dict]:
    with open("data/golden_questions.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- router ----------

@pytest.mark.parametrize("q", golden(), ids=lambda q: q["id"])
def test_offline_router_matches_golden_route(q):
    assert _route_offline(q["question"]) == q["expected_route"]


# ---------- chunker ----------

def test_split_keeps_short_text_whole():
    assert _split("short text") == ["short text"]


def test_split_cuts_long_text_with_overlap():
    pieces = _split("x" * 3000)
    assert [len(p) for p in pieces] == [1500, 1500, 400]


def test_tables_stay_whole_and_new_heading_starts_new_chunk():
    blocks = [
        Block("Intro text", "paragraph", "Purpose"),
        Block("More intro", "paragraph", "Purpose"),
        Block("A | B\n1 | 2", "table", "Table"),
        Block("Scope text", "paragraph", "Scope"),
    ]
    chunks = chunk_blocks(blocks)
    assert [c["kind"] for c in chunks] == ["paragraph", "table", "paragraph"]
    assert chunks[0]["text"] == "Intro text\nMore intro"
    assert chunks[1]["text"] == "A | B\n1 | 2"


def test_header_names_document_and_section():
    text = add_header("TAX-POL-014", {"section": "Renewal", "kind": "paragraph", "text": "Body"})
    assert text.startswith("Document: TAX-POL-014\nSection: Renewal")
    assert text.endswith("\n\nBody")


# ---------- search helpers ----------

def test_terms_drops_filler_words_and_punctuation():
    assert _terms("When do exemption certificates expire?") == ["exemption", "certificates", "expire"]


def test_rrf_rewards_results_found_by_both_searches():
    keyword = [{"chunk_id": 1}, {"chunk_id": 2}]
    meaning = [{"chunk_id": 3}, {"chunk_id": 4}, {"chunk_id": 5}, {"chunk_id": 6}, {"chunk_id": 2}]
    assert _rrf(keyword, meaning)[0]["chunk_id"] == 2


def test_overlap_is_share_of_question_words_found():
    assert _overlap(["sar", "deadline"], "The SAR is due") == 0.5