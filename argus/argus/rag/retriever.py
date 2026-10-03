"""
RAG retriever module for fetching regulatory passages during classification.
Provides framework-specific vector similarity search.
"""
import logging

from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy.engine import make_url
import logging

logger = logging.getLogger(__name__)


class RegulatoryRetriever:
    """
    Retrieves regulatory passages from vector store for RAG context.
    Manages lazy-loaded PGVector stores per framework.
    """

    def __init__(self, db_url: str):
        """
        Initialize retriever with embeddings.
        
        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = make_url(db_url).set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        )
        self.stores = {}  # Cache of loaded stores

    def retrieve(
        self,
        framework: str,
        query: str,
        k: int = 5,
    ) -> list[Document]:
        """
        Retrieve relevant passages for a query.
        
        Args:
            framework: Framework name (EU_AI_ACT, RBI, etc.)
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant Document objects, empty if collection not found
        """
        collection_name = f"regulations_{framework.lower()}"

        # Try to get or create store
        if collection_name not in self.stores:
            try:
                # Lazy import PGVector to avoid importing psycopg/libpq at module import time
                from langchain_postgres import PGVector

                self.stores[collection_name] = PGVector(
                    connection=self.db_url,
                    embeddings=self.embeddings,
                    collection_name=collection_name,
                )
            except Exception as e:
                logger.warning(
                    f"Could not load collection {collection_name}: {e}. "
                    f"Regulatory documents may not be ingested yet."
                )
                return []

        try:
            store = self.stores[collection_name]
            # Similarity search
            results = store.similarity_search(query, k=k)
            logger.debug(f"Retrieved {len(results)} passages for: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error retrieving from {collection_name}: {e}")
            return []

    def format_passages(self, docs: list[Document]) -> str:
        """
        Format retrieved passages for LLM context.
        
        Args:
            docs: List of Document objects
            
        Returns:
            Formatted string with passages and sources
        """
        if not docs:
            return "No relevant regulatory passages found in knowledge base."

        formatted = []
        for i, doc in enumerate(docs, 1):
            article = doc.metadata.get("citation", doc.metadata.get("article", "Unknown"))
            source = doc.metadata.get("source", "Unknown")
            if "page_number" in doc.metadata:
                source += f", p. {doc.metadata['page_number']}"
            content = doc.page_content.strip()

            formatted.append(f"[{article} - {source}]\n{content}")

        return "\n\n---\n\n".join(formatted)
