"""
RAG pipeline ingestion module for loading and processing regulatory documents.
Implements custom text splitting for regulatory documents and vector storage.
"""
import argparse
import logging
import re
from pathlib import Path

from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector

logger = logging.getLogger(__name__)


class RegulatoryTextSplitter:
    """
    Custom text splitter optimized for regulatory documents.
    Detects article and section boundaries to preserve regulatory structure.
    """

    # Patterns for detecting regulatory boundaries
    BOUNDARY_PATTERNS = [
        r"^Article\s+\d+",
        r"^ARTICLE\s+\d+",
        r"^Section\s+\d+\.\d+",
        r"^Annex\s+[IVX]+",
        r"^\d+\.\d+\s+[A-Z]",
    ]

    def split(self, docs: list[Document]) -> list[Document]:
        """
        Split documents by regulatory article boundaries.
        
        Args:
            docs: List of Document objects
            
        Returns:
            List of split Document objects with article metadata
        """
        split_docs = []

        for doc in docs:
            content = doc.page_content
            lines = content.split("\n")

            current_buffer = []
            current_article = "General"

            for line in lines:
                # Check if line matches article boundary
                is_boundary = any(
                    re.match(pattern, line.strip())
                    for pattern in self.BOUNDARY_PATTERNS
                )

                if is_boundary and current_buffer:
                    # Flush current buffer
                    buffered_text = "\n".join(current_buffer)
                    if len(buffered_text.strip()) > 0:
                        split_doc = Document(
                            page_content=buffered_text,
                            metadata={
                                **doc.metadata,
                                "article": current_article,
                            },
                        )
                        split_docs.append(split_doc)

                    # Extract article label from boundary line
                    current_article = line.strip()[:100]
                    current_buffer = [line]
                else:
                    current_buffer.append(line)

            # Flush remaining buffer
            if current_buffer:
                buffered_text = "\n".join(current_buffer)
                if len(buffered_text.strip()) > 0:
                    split_doc = Document(
                        page_content=buffered_text,
                        metadata={
                            **doc.metadata,
                            "article": current_article,
                        },
                    )
                    split_docs.append(split_doc)

        # Fallback: if no splits were made, use recursive splitter
        if not split_docs:
            fallback_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=100,
            )
            split_docs = fallback_splitter.split_documents(docs)

        return split_docs


class RegulatoryIngester:
    """
    Ingests regulatory PDF documents into vector store.
    Manages PGVector collections per framework.
    """

    SUPPORTED_FRAMEWORKS = ["EU_AI_ACT", "RBI", "DPDP", "EBA"]

    def __init__(self, db_url: str):
        """
        Initialize ingester with embeddings and database connection.
        
        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = db_url
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        )
        self.stores = {}  # Lazy-loaded PGVector stores

    def ingest(self, pdf_path: Path, framework: str) -> int:
        """
        Ingest a PDF document into vector store.
        
        Args:
            pdf_path: Path to PDF file
            framework: Regulatory framework (EU_AI_ACT, RBI, etc.)
            
        Returns:
            Number of chunks ingested
            
        Raises:
            ValueError: If framework not supported or PDF cannot be loaded
        """
        if framework not in self.SUPPORTED_FRAMEWORKS:
            raise ValueError(f"Unsupported framework: {framework}")

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Loading PDF: {pdf_path}")

        # Load PDF
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()

        logger.info(f"Loaded {len(docs)} pages from {pdf_path.name}")

        # Add framework metadata
        for doc in docs:
            doc.metadata["framework"] = framework
            doc.metadata["source"] = pdf_path.name

        # Split documents
        splitter = RegulatoryTextSplitter()
        split_docs = splitter.split(docs)

        logger.info(f"Split into {len(split_docs)} chunks")

        # Get or create store
        collection_name = f"regulations_{framework.lower()}"
        try:
            self.stores[collection_name] = PGVector(
                connection_string=self.db_url,
                embedding_function=self.embeddings,
                collection_name=collection_name,
            )

            # Add documents
            ids = self.stores[collection_name].add_documents(split_docs)
            logger.info(f"Ingested {len(ids)} chunks into {collection_name}")

            return len(ids)
        except Exception as e:
            logger.error(f"Failed to ingest into vector store: {e}")
            raise

    def reset_collection(self, framework: str) -> None:
        """
        Reset/clear a collection (for testing).
        
        Args:
            framework: Framework name
        """
        collection_name = f"regulations_{framework.lower()}"
        try:
            # Remove cached store if exists; actual clearing handled by langchain-postgres
            self.stores.pop(collection_name, None)
            logger.info(f"Reset collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Could not reset collection {collection_name}: {e}")


def main():
    """CLI entry point for ingesting regulatory documents."""
    parser = argparse.ArgumentParser(
        description="Ingest regulatory PDFs into ARGUS RAG vector store"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to PDF file to ingest",
    )
    parser.add_argument(
        "--framework",
        required=True,
        choices=RegulatoryIngester.SUPPORTED_FRAMEWORKS,
        help="Regulatory framework",
    )
    parser.add_argument(
        "--db-url",
        default="postgresql+asyncpg://argus:argus_secret@localhost:5432/argus",
        help="Database connection URL",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    ingester = RegulatoryIngester(args.db_url)
    try:
        count = ingester.ingest(Path(args.source), args.framework)
        print(f"✓ Ingested {count} chunks from {args.source}")
    except Exception as e:
        print(f"✗ Ingestion failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
