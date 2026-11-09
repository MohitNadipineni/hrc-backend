MAX_CHARS = 1500
OVERLAP = 200


def _split(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + MAX_CHARS])
        start += MAX_CHARS - OVERLAP
    return out


def chunk_blocks(blocks) -> list[dict]:
    chunks, buf, section = [], [], None

    def flush():
        if buf:
            for piece in _split("\n".join(buf)):
                chunks.append({"kind": "paragraph", "section": section, "text": piece})
            buf.clear()

    for b in blocks:
        if b.kind in ("table", "slide"):
            flush()
            chunks.append({"kind": b.kind, "section": b.section, "text": b.text})
            continue
        if b.section != section or sum(map(len, buf)) + len(b.text) > MAX_CHARS:
            flush()
            section = b.section
        buf.append(b.text)
    flush()
    return chunks


def add_header(doc_id: str, chunk: dict) -> str:
    return (f"Document: {doc_id}\n"
            f"Section: {chunk['section']}\n"
            f"Type: {chunk['kind']}\n\n{chunk['text']}")