"""
Embeddings factory: returns the appropriate embeddings model based on config.
"""
import logging
from functools import lru_cache
from backend.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embeddings():
    """Return cached embeddings instance."""
    settings = get_settings()

    if settings.embedding_provider == "local" or not settings.openai_api_key:
        logger.info("Using local HuggingFace embeddings: %s", settings.embedding_model)
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as exc:
            logger.error("Failed to load HuggingFace embeddings: %s", exc)
            raise

    logger.info("Using OpenAI embeddings: %s", settings.embedding_model)
    try:
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
        )
    except Exception as exc:
        logger.warning("OpenAI embeddings failed, falling back to local: %s", exc)
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
