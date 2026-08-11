"""
Vector store: manages the ChromaDB instance.
Persists to disk; does NOT rebuild on every startup.
"""
import logging
import os
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from backend.config import get_settings
from backend.rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)


def _chroma_path_has_data(chroma_path: str) -> bool:
    """Return True if the Chroma directory contains at least one collection."""
    p = Path(chroma_path)
    if not p.exists():
        return False
    # ChromaDB persists a sqlite3 file
    return any(p.rglob("*.sqlite3")) or any(p.rglob("chroma.sqlite3"))


def get_or_create_vectorstore(force_rebuild: bool = False):
    """
    Return a ChromaDB vector store.
    - If the DB already exists on disk, load it without rebuilding.
    - If it does not exist or force_rebuild=True, rebuild from knowledge base docs.
    """
    settings = get_settings()
    chroma_path = settings.absolute_chroma_path
    collection_name = settings.chroma_collection_name
    embeddings = get_embeddings()

    try:
        import chromadb
        from langchain_community.vectorstores import Chroma

        if not force_rebuild and _chroma_path_has_data(chroma_path):
            logger.info("Loading existing ChromaDB from: %s", chroma_path)
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=chroma_path,
            )
            try:
                count = vectorstore._collection.count()
            except Exception:
                count = len(vectorstore.get()["ids"]) if vectorstore.get() else 0
            logger.info("ChromaDB loaded with %d documents", count)
            if count > 0:
                return vectorstore
            logger.info("ChromaDB empty — rebuilding from knowledge base.")

        logger.info("Building ChromaDB from knowledge base documents...")
        from backend.rag.loader import load_documents
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        raw_docs = load_documents(settings.knowledge_base_path)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(raw_docs)
        logger.info("Split into %d chunks", len(chunks))

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=chroma_path,
        )
        logger.info("ChromaDB built and persisted with %d chunks", len(chunks))
        return vectorstore

    except Exception as exc:
        logger.error("Vector store error: %s", exc)
        raise


# Module-level cached instance
_vectorstore = None


def get_vectorstore(force_rebuild: bool = False):
    """Return module-level cached vectorstore."""
    global _vectorstore
    if _vectorstore is None or force_rebuild:
        _vectorstore = get_or_create_vectorstore(force_rebuild=force_rebuild)
    return _vectorstore
