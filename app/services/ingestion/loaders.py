from dataclasses import dataclass
from pathlib import Path

import docx
import pdfplumber
from pptx import Presentation


@dataclass
class Block:
    text: str
    kind: str      # "paragraph", "table" or "slide"
    section: str   # nearest heading, page or slide title


def load_docx(path: Path) -> list[Block]:
    d = docx.Document(path)
    blocks, section = [], ""
    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        style_name = p.style.name if p.style is not None else ""
        if style_name.startswith("Heading"):
            section = t
            continue
        blocks.append(Block(t, "paragraph", section))
    for table in d.tables:
        rows = [" | ".join(c.text.strip() for c in r.cells) for r in table.rows]
        blocks.append(Block("\n".join(rows), "table", "Table"))
    return blocks


def load_pdf(path: Path) -> list[Block]:
    blocks = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                blocks.append(Block(text, "paragraph", f"Page {i}"))
            for tbl in page.extract_tables():
                rows = [" | ".join(c or "" for c in r) for r in tbl]
                blocks.append(Block("\n".join(rows), "table", f"Page {i}"))
    return blocks


def load_pptx(path: Path) -> list[Block]:
    blocks = []
    for i, slide in enumerate(Presentation(path).slides, 1):
        title = slide.shapes.title.text if slide.shapes.title else f"Slide {i}"
        parts = [s.text_frame.text for s in slide.shapes
                 if s.has_text_frame and s.text_frame.text.strip()]
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                parts.append("Speaker notes: " + notes)
        blocks.append(Block("\n".join(parts), "slide", title))
    return blocks


LOADERS = {".docx": load_docx, ".pdf": load_pdf, ".pptx": load_pptx}