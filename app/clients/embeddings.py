import hashlib
import math

from app.core.config import settings


def _fake_embed(text: str, dim: int) -> list[float]:
    """Offline stand-in: same text -> same vector. No real meaning."""
    vec, seed = [], hashlib.sha256(text.encode()).digest()
    while len(vec) < dim:
        seed = hashlib.sha256(seed).digest()
        vec.extend((b - 127.5) / 127.5 for b in seed)
    vec = vec[:dim]
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if settings.llm_provider == "offline":
        return [_fake_embed(t, settings.embedding_dim) for t in texts]
    from langchain_openai import AzureOpenAIEmbeddings
    emb = AzureOpenAIEmbeddings(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_embedding_deployment,
        dimensions=settings.embedding_dim,
    )
    return emb.embed_documents(texts)