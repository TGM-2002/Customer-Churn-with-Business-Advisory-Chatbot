"""
document_store.py
------------------
ChromaDB vector store for banking strategy and retention documents.

Responsibilities
----------------
- Initialise a persistent ChromaDB collection
- Ingest strategy documents (PDF, TXT, MD) with chunking
- Expose retrieve() returning the top-k most relevant chunks for a query,
  optionally biased by customer context (risk tier, segment) — used by the
  advisor to ground its responses in the bank's own institutional knowledge

Dependencies
------------
    pip install chromadb sentence-transformers pypdf

Usage
-----
    from src.ai_advisor.rag.document_store import RAGDocumentStore

    store = RAGDocumentStore()
    store.ingest_directory("data/strategy_documents")

    docs = store.retrieve(
        "customer has zero balance and is inactive",
        top_k=5,
        customer_context={"risk_tier": "Critical", "segment": "Mass"},
    )
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config — override via constructor if needed
# ---------------------------------------------------------------------------

DEFAULT_PERSIST_DIR = "data/chroma_db"
DEFAULT_COLLECTION  = "banking_strategy"
DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE          = 500
CHUNK_OVERLAP       = 50


class RAGDocumentStore:
    """
    Wraps a persistent ChromaDB collection with ingestion and retrieval,
    purpose-built for grounding the ChurnAdvisor's retention recommendations.
    """

    def __init__(
        self,
        persist_dir: str = DEFAULT_PERSIST_DIR,
        collection: str  = DEFAULT_COLLECTION,
        embed_model: str = DEFAULT_EMBED_MODEL,
        chunk_size: int  = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.persist_dir   = Path(persist_dir)
        self.chunk_size    = chunk_size
        self.chunk_overlap = chunk_overlap

        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )

        self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embed_model
        )

        self.collection = self.client.get_or_create_collection(
            name=collection,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

        log.info(
            f"RAGDocumentStore ready — collection: '{collection}'  "
            f"docs: {self.collection.count()}  persist: {self.persist_dir}"
        )

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_directory(self, directory: str, glob: str = "**/*") -> int:
        """Recursively ingest all supported files (.pdf, .txt, .md) in a folder."""
        path  = Path(directory)
        files = [
            p for p in path.glob(glob)
            if p.is_file() and p.suffix.lower() in {".pdf", ".txt", ".md"}
        ]

        if not files:
            log.warning(f"No supported files found in {directory}")
            return 0

        total = 0
        for f in files:
            added = self.ingest_file(f)
            total += added
            log.info(f"  {f.name}: {added} chunks added")

        log.info(f"Ingestion complete — {total} total chunks across {len(files)} files")
        return total

    def ingest_file(self, path: Path) -> int:
        path = Path(path)
        text = self._read_file(path)
        if not text.strip():
            log.warning(f"Empty file skipped: {path}")
            return 0

        chunks = self._chunk(text)
        return self._upsert_chunks(chunks, source=path.name)

    def ingest_text(self, text: str, source: str = "manual") -> int:
        chunks = self._chunk(text)
        return self._upsert_chunks(chunks, source=source)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        customer_context: Optional[dict] = None,
    ) -> list[dict]:
        """
        Return the top-k most relevant chunks for a query, optionally biased
        toward the customer's risk tier and segment.

        Parameters
        ----------
        query             : the base retrieval query (e.g. built from SHAP drivers)
        top_k             : number of chunks to return
        customer_context  : optional dict with 'risk_tier' and/or 'segment',
                            appended to the query to bias retrieval toward
                            strategy content written for that customer's profile

        Returns
        -------
        list of dicts with keys: 'doc_id', 'content', 'score'
        """
        if self.collection.count() == 0:
            log.warning("Collection is empty — ingest documents first.")
            return []

        effective_query = query
        if customer_context:
            bias_terms = " ".join(
                str(v) for v in (
                    customer_context.get("risk_tier"),
                    customer_context.get("segment"),
                ) if v
            )
            if bias_terms:
                effective_query = f"{query} {bias_terms}"

        results = self.collection.query(
            query_texts=[effective_query],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        docs = []
        for content, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            source      = meta.get("source", "unknown")
            chunk_index = meta.get("chunk_index", 0)
            docs.append({
                "doc_id":  f"{source}#{chunk_index}",
                "content": content,
                "score":   round(1 - dist, 4),
            })

        return docs

    def count(self) -> int:
        return self.collection.count()

    def clear(self) -> None:
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("Collection cleared.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_file(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._read_pdf(path)
        return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _read_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            log.warning("pypdf not installed — skipping PDF. Run: pip install pypdf")
            return ""
        except Exception as e:
            log.error(f"Failed to read PDF {path}: {e}")
            return ""

    def _chunk(self, text: str) -> list[str]:
        text = re.sub(r"\s+", " ", text).strip()

        chunks = []
        start  = 0
        while start < len(text):
            end = start + self.chunk_size

            if end < len(text):
                boundary = text.rfind(". ", start, end)
                if boundary != -1 and boundary > start + self.chunk_size // 2:
                    end = boundary + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.chunk_overlap

        return chunks

    def _upsert_chunks(self, chunks: list[str], source: str) -> int:
        ids, docs, metas = [], [], []

        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(chunk.encode()).hexdigest()
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append({"source": source, "chunk_index": i})

        if not ids:
            return 0

        self.collection.upsert(ids=ids, documents=docs, metadatas=metas)
        return len(ids)


# ---------------------------------------------------------------------------
# CLI — ingest a directory from the command line
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        stream=sys.stdout,
    )

    parser = argparse.ArgumentParser(description="Ingest banking strategy documents into ChromaDB")
    parser.add_argument("--docs-dir",    default="data/strategy_documents")
    parser.add_argument("--persist-dir", default=DEFAULT_PERSIST_DIR)
    parser.add_argument("--query",       default=None)
    args = parser.parse_args()

    store = RAGDocumentStore(persist_dir=args.persist_dir)
    store.ingest_directory(args.docs_dir)
    log.info(f"Total chunks in collection: {store.count()}")

    if args.query:
        log.info(f"\nTest query: '{args.query}'")
        results = store.retrieve(args.query, top_k=3)
        for i, r in enumerate(results, 1):
            log.info(f"\n[{i}] score={r['score']}  doc_id={r['doc_id']}")
            log.info(f"    {r['content'][:200]}...")