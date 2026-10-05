"""
RAG retriever module for fetching regulatory passages during classification.
Provides framework-specific vector similarity search.
"""
import logging

from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine, text

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
        self.engine = create_engine(self.db_url)

    def has_corpus(self, framework: str) -> bool:
        with self.engine.connect() as connection:
            return bool(connection.execute(text(
                "SELECT EXISTS (SELECT 1 FROM langchain_pg_embedding e "
                "JOIN langchain_pg_collection c ON c.uuid=e.collection_id WHERE c.name=:name)"
            ), {"name": f"regulations_{framework.lower()}"}).scalar())

    def retrieve_for_classification_with_score(self, framework, query, k=5):
        if k < 2:
            raise ValueError("Classification retrieval requires at least two slots")
        if not self.has_corpus(framework):
            return []
        # Initialize the existing store without changing its distance strategy.
        self.retrieve(framework, query, k=1)
        store = self.stores[f"regulations_{framework.lower()}"]
        if framework != "EU_AI_ACT":
            return store.similarity_search_with_score(query, k=k)
        selected = []
        for filter in (
            {"section_type": "article", "article_number": 6},
            {"section_type": "annex", "annex_id": "III"},
        ):
            pinned = store.similarity_search_with_score(query, k=1, filter=filter)
            if not pinned:
                raise RuntimeError("EU classification requires indexed Article 6 and Annex III")
            selected.extend(pinned)
        candidates = store.similarity_search_with_score(
            query, k=k+2, filter={"section_type": {"$in": ["article", "annex"]}},
        )
        identities = {(doc.page_content, str(doc.metadata)) for doc, _ in selected}
        for doc, distance in candidates:
            identity = (doc.page_content, str(doc.metadata))
            if identity not in identities and len(selected) < k:
                selected.append((doc, distance))
                identities.add(identity)
        return sorted(selected, key=lambda item: item[1])

    def retrieve_for_classification(self, framework, query, k=5):
        return [doc for doc, _ in self.retrieve_for_classification_with_score(framework, query, k)]

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
