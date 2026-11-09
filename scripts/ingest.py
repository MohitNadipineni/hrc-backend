from pathlib import Path

import numpy as np

from app.clients.embeddings import embed_texts
from app.core.config import settings
from app.repositories.chunks import replace_document_chunks
from app.services.ingestion.chunker import add_header, chunk_blocks
from app.services.ingestion.loaders import LOADERS

DOC_GROUPS = {
    "AML-SOP-021": ["compliance"],
}
def main() -> None:
    for path in sorted(Path(settings.sharepoint_dir).iterdir()):
        loader = LOADERS.get(path.suffix.lower())
        if loader is None:
            print(f"skip {path.name}")
            continue

        doc_id = path.stem.split("_")[0]                    # TAX-POL-014
        doc_title = path.stem.split("_", 1)[-1].replace("_", " ")

        chunks = chunk_blocks(loader(path))
        texts = [add_header(doc_id, c) for c in chunks]
        vectors = embed_texts(texts)

        rows = [
            (doc_id, doc_title, str(path), c["kind"], c["section"], i, t,
             DOC_GROUPS.get(doc_id, ["all"]), np.array(v, dtype=np.float32))
            for i, (c, t, v) in enumerate(zip(chunks, texts, vectors))
        ]
        replace_document_chunks(doc_id, rows)
        print(f"{doc_id}: {len(rows)} chunks saved")


if __name__ == "__main__":
    main()