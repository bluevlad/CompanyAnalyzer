"""Mention 텍스트를 ChromaDB에 인덱싱하는 RAG 서비스.

- 컬렉션명: company_{target_id}_mentions (target별 분리)
- 임베딩: Ollama (`EMBEDDING_MODEL`, 기본 nomic-embed-text)
- 청크: 800자 / 100자 오버랩
- 동기 ChromaDB 클라이언트는 run_in_executor로 wrap

AllergyInsight `RAGService` 패턴을 차용하되, mention 도메인에 맞춰 단순화.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.models import Mention, RagChunk

logger = logging.getLogger(__name__)
settings = get_settings()

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []
    text = text.strip()
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start += size - overlap
    return chunks


def _collection_name(target_id: int) -> str:
    return f"company_{target_id}_mentions"


class RagIndexerService:
    """Mention 본문 → ChromaDB 적재 및 검색."""

    def __init__(self) -> None:
        self._client = None
        self._available: Optional[bool] = None
        self._ollama = None  # lazy

    # ─────────────────────── lifecycle ──────────────────────────────────

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import chromadb

            persist_dir = os.path.abspath(settings.CHROMADB_PERSIST_DIR)
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
            self._available = True
            logger.info("ChromaDB ready at %s", persist_dir)
        except Exception as exc:
            logger.warning("ChromaDB init failed: %s", exc)
            self._available = False
        return self._client

    def _get_collection(self, target_id: int):
        client = self._get_client()
        if client is None:
            return None
        return client.get_or_create_collection(
            name=_collection_name(target_id),
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def is_available(self) -> bool:
        if self._available is None:
            self._get_client()
        return bool(self._available)

    # ─────────────────────── embeddings ────────────────────────────────

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """Ollama embeddings (sync SDK call → run_in_executor)."""
        if self._ollama is None:
            import ollama as ollama_lib

            self._ollama = ollama_lib.AsyncClient(host=settings.OLLAMA_BASE_URL)

        results: list[list[float]] = []
        for text in texts:
            try:
                resp = await self._ollama.embeddings(
                    model=settings.EMBEDDING_MODEL, prompt=text
                )
                results.append(resp.get("embedding") or [])
            except Exception as exc:
                logger.warning("embedding failed: %s", exc)
                results.append([])
        return results

    # ─────────────────────── indexing ──────────────────────────────────

    async def index_mention(self, session: AsyncSession, mention: Mention) -> int:
        """단건 멘션 → 청킹 → 임베딩 → ChromaDB add → RagChunk 메타 저장.

        Returns:
            적재된 청크 수
        """
        if not self.is_available:
            return 0

        full_text = "\n\n".join(filter(None, [mention.title, mention.raw_content]))
        chunks = _chunk_text(full_text)
        if not chunks:
            return 0

        embeddings = await self._embed(chunks)
        # 임베딩 빈 값(에러)인 청크 제외
        filtered = [
            (chunk, emb)
            for chunk, emb in zip(chunks, embeddings)
            if emb
        ]
        if not filtered:
            return 0

        loop = asyncio.get_running_loop()
        collection = await loop.run_in_executor(
            None, self._get_collection, mention.target_id
        )
        if collection is None:
            return 0

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        records: list[RagChunk] = []

        for idx, (chunk_text, emb) in enumerate(filtered):
            chroma_id = f"mention_{mention.id}_chunk_{idx}"
            ids.append(chroma_id)
            documents.append(chunk_text)
            metadatas.append(
                {
                    "mention_id": mention.id,
                    "target_id": mention.target_id,
                    "title": (mention.title or "")[:200],
                    "url": (mention.url or "")[:500],
                    "source": mention.source_name or "",
                    "published_at": (
                        mention.published_at.isoformat() if mention.published_at else ""
                    ),
                    "chunk_index": idx,
                }
            )
            records.append(
                RagChunk(
                    mention_id=mention.id,
                    chunk_index=idx,
                    text=chunk_text,
                    token_count=len(chunk_text.split()),
                    chroma_id=chroma_id,
                )
            )

        # ChromaDB add는 동기 — executor wrap
        def _add():
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=[emb for _, emb in filtered],
            )

        await loop.run_in_executor(None, _add)

        for rec in records:
            session.add(rec)
        await session.commit()
        logger.info("indexed mention=%s chunks=%s", mention.id, len(records))
        return len(records)

    # ─────────────────────── search ────────────────────────────────────

    async def search(
        self, target_id: int, query: str, k: int = 5
    ) -> list[dict]:
        """target의 컬렉션에서 query에 가장 가까운 청크 k개를 반환."""
        if not self.is_available:
            return []

        loop = asyncio.get_running_loop()
        collection = await loop.run_in_executor(None, self._get_collection, target_id)
        if collection is None:
            return []

        emb = (await self._embed([query]))[0]
        if not emb:
            return []

        def _query():
            return collection.query(query_embeddings=[emb], n_results=k)

        try:
            results = await loop.run_in_executor(None, _query)
        except Exception as exc:
            logger.warning("chroma query failed: %s", exc)
            return []

        out: list[dict] = []
        if results and results.get("ids") and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = (results.get("metadatas") or [[]])[0][i] or {}
                distance = (results.get("distances") or [[1.0]])[0][i]
                out.append(
                    {
                        "chroma_id": doc_id,
                        "text": (results.get("documents") or [[]])[0][i],
                        "score": round(max(0.0, 1.0 - float(distance)), 4),
                        "mention_id": meta.get("mention_id"),
                        "title": meta.get("title", ""),
                        "url": meta.get("url", ""),
                        "source": meta.get("source", ""),
                        "published_at": meta.get("published_at", ""),
                    }
                )
        return out


_singleton: Optional[RagIndexerService] = None


def get_rag_indexer() -> RagIndexerService:
    global _singleton
    if _singleton is None:
        _singleton = RagIndexerService()
    return _singleton
