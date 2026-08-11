"""
Retriever: wraps the ChromaDB vectorstore with a similarity search.
"""
import logging
from typing import List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def retrieve_documents(query: str, k: int = 5) -> List[Document]:
    """
    Retrieve top-k relevant documents for a given query.
    Returns empty list on failure (graceful degradation).
    """
    try:
        from backend.rag.vectorstore import get_vectorstore
        vectorstore = get_vectorstore()
        docs = vectorstore.similarity_search(query, k=k)
        logger.info("Retrieved %d documents for query: %.60s...", len(docs), query)
        return docs
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        return []


def retrieve_with_scores(query: str, k: int = 5) -> List[tuple]:
    """Retrieve documents with similarity scores."""
    try:
        from backend.rag.vectorstore import get_vectorstore
        vectorstore = get_vectorstore()
        return vectorstore.similarity_search_with_relevance_scores(query, k=k)
    except Exception as exc:
        logger.error("Scored retrieval failed: %s", exc)
        return []


def format_context(docs: List[Document]) -> str:
    """Format retrieved documents into a single context string for the LLM."""
    if not docs:
        return "No relevant documentation found in knowledge base."
    parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "Unknown")
        parts.append(f"[Source {i}: {source}]\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(parts)
