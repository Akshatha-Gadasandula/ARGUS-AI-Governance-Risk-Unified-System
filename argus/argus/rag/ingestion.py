"""
RAG pipeline ingestion module for loading and processing regulatory documents.
Implements custom text splitting for regulatory documents and vector storage.
"""
import argparse
import logging
import re
from pathlib import Path

from langchain.schema import Document
import pymupdf
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from sqlalchemy.engine import make_url

logger = logging.getLogger(__name__)


def load_pdf_documents(pdf_path: Path) -> list[Document]:
    """Extract readable text and retain bold-line hints for wrapped titles."""
    docs = []
    with pymupdf.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf):
            bold_lines = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    spans = [span for span in line["spans"] if span["text"].strip()]
                    if spans and all(span["flags"] & 16 for span in spans):
                        bold_lines.append("".join(span["text"] for span in line["spans"]).strip())
            docs.append(Document(
                page_content=page.get_text(),
                metadata={"page": page_number, "_bold_lines": bold_lines},
            ))
    return docs


class RegulatoryTextSplitter:
    """Preserve cross-page provisions and bound heading-prefixed model input."""

    ARTICLE = re.compile(r"Article\s+(\d+)", re.I)
    ANNEX = re.compile(r"ANNEX\s+([IVXLCDM]+)", re.I)
    STRUCTURE = re.compile(r"(?:CHAPTER\s+[IVXLCDM]+|SECTION\s+\d+)", re.I)
    FOOTER = re.compile(r"(?:OJ L,.*|EN|ELI:.*|\d+/\d+)")

    def __init__(self, tokenizer, max_tokens: int, overlap_tokens: int = 24):
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    @staticmethod
    def _title(records, heading_index):
        """Consume wrapped bold title lines, including text such as 'Article 49'."""
        index = heading_index + 1
        if index >= len(records):
            return "", index
        parts = [records[index][0]]
        first_is_bold = records[index][2]
        index += 1
        while first_is_bold and index < len(records) and records[index][2]:
            parts.append(records[index][0])
            index += 1
        return " ".join(parts).strip(" `"), index

    @staticmethod
    def _heading(metadata):
        if metadata["section_type"] == "article":
            citation = f"Article {metadata['article_number']}"
        elif metadata["section_type"] == "annex":
            citation = f"Annex {metadata['annex_id']}"
            if metadata.get("annex_point"):
                citation += f", point {metadata['annex_point']}"
                if metadata.get("annex_subpoint"):
                    citation += f"({metadata['annex_subpoint']})"
        else:
            citation = "Recitals"
        return citation, f"{citation} - {metadata['title']}" if metadata["title"] else citation

    def _subsplit(self, lines, metadata):
        """Use original tokenizer offsets, counting headings and special tokens."""
        body = ""
        spans = []
        for line, page in lines:
            line = re.sub(r"\s+", " ", line).strip()
            start = len(body) + (1 if body else 0)
            body += (" " if body else "") + line
            spans.append((start, len(body), page))
        if not body:
            return []
        citation, heading = self._heading(metadata)
        prefix = heading + "\n"
        budget = (
            self.max_tokens
            - self.tokenizer.num_special_tokens_to_add(False)
            - len(self.tokenizer.encode(prefix, add_special_tokens=False))
        )
        if budget <= self.overlap_tokens:
            raise ValueError(f"Heading leaves insufficient token budget: {heading}")
        offsets = self.tokenizer(
            body, add_special_tokens=False, truncation=False, return_offsets_mapping=True,
            verbose=False,
        )["offset_mapping"]
        chunks = []
        start = 0
        while start < len(offsets):
            end = min(start + budget, len(offsets))
            # Keep whole words at window boundaries whenever possible.
            if end < len(offsets):
                while end > start + 1 and offsets[end - 1][1] == offsets[end][0]:
                    end -= 1
            while end > start:
                first, last = offsets[start][0], offsets[end - 1][1]
                content = prefix + body[first:last]
                if len(self.tokenizer.encode(content, truncation=False)) <= self.max_tokens:
                    break
                end -= 1
            if end == start:
                raise ValueError(f"Unable to fit text under token limit: {heading}")
            pages = [page for a, b, page in spans if a < last and b > first]
            chunks.append(Document(page_content=content, metadata={
                **metadata,
                "citation": citation,
                "page": pages[0],
                "page_end": pages[-1],
                "page_number": pages[0] + 1,
                "page_number_end": pages[-1] + 1,
                "chunk_index": len(chunks),
            }))
            if end == len(offsets):
                break
            next_start = max(start + 1, end - self.overlap_tokens)
            while next_start > start + 1 and offsets[next_start - 1][1] == offsets[next_start][0]:
                next_start -= 1
            start = next_start
        return chunks

    def split(self, docs: list[Document]) -> list[Document]:
        """Read exact standalone headings; references inside prose are not headings."""
        records = []
        for doc in docs:
            bold_lines = set(doc.metadata.get("_bold_lines", []))
            for line in doc.page_content.splitlines():
                line = line.strip()
                if line and not self.FOOTER.fullmatch(line):
                    records.append((line, doc.metadata["page"], line in bold_lines))
        if not records:
            return []
        base = {k: v for k, v in docs[0].metadata.items() if k != "page" and not k.startswith("_")}
        metadata = {
            **base, "section_type": "recital", "article": "Recitals",
            "article_number": None, "article_title": None, "annex_id": None,
            "annex_title": None, "annex_point": None, "annex_subpoint": None,
            "title": "",
        }
        chunks, buffer = [], []
        index = 0
        while index < len(records):
            line, page, _ = records[index]
            article = self.ARTICLE.fullmatch(line)
            annex = self.ANNEX.fullmatch(line)
            if article or annex:
                chunks.extend(self._subsplit(buffer, metadata))
                buffer = []
                title, next_index = self._title(records, index)
                metadata = {
                    **base, "section_type": "article" if article else "annex",
                    "article": f"Article {article[1]}" if article else f"Annex {annex[1].upper()}",
                    "article_number": int(article[1]) if article else None,
                    "article_title": title if article else None,
                    "annex_id": annex[1].upper() if annex else None,
                    "annex_title": title if annex else None,
                    "annex_point": None, "annex_subpoint": None,
                    "title": title, "heading_page": page,
                }
                index = next_index
                continue
            if self.STRUCTURE.fullmatch(line):
                # Chapter/section labels and their titles are not provision text.
                _, index = self._title(records, index)
                continue
            if metadata["annex_id"] == "III":
                area = re.fullmatch(r"(\d+)\.\s*(.*)", line)
                subpoint = re.match(r"\(([a-z])\)\s+", line)
                if area or (subpoint and metadata["annex_point"]):
                    chunks.extend(self._subsplit(buffer, metadata))
                    buffer = []
                    metadata = {**metadata}
                    if area:
                        metadata.update(annex_point=area[1], annex_subpoint=None)
                    else:
                        metadata["annex_subpoint"] = subpoint[1]
            buffer.append((line, page))
            index += 1
        chunks.extend(self._subsplit(buffer, metadata))
        return chunks


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
        self.db_url = make_url(db_url).set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
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
        docs = load_pdf_documents(pdf_path)

        logger.info(f"Loaded {len(docs)} pages from {pdf_path.name}")

        # Add framework metadata
        for doc in docs:
            doc.metadata["framework"] = framework
            doc.metadata["source"] = pdf_path.name

        # Split documents
        splitter = RegulatoryTextSplitter(
            self.embeddings.client.tokenizer, self.embeddings.client.max_seq_length,
        )
        split_docs = splitter.split(docs)

        logger.info(f"Split into {len(split_docs)} chunks")

        # Get or create store
        collection_name = f"regulations_{framework.lower()}"
        try:
            self.stores[collection_name] = PGVector(
                connection=self.db_url,
                embeddings=self.embeddings,
                collection_name=collection_name,
                # Replace this framework's collection so reruns cannot append duplicates.
                pre_delete_collection=True,
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
        default="postgresql+psycopg://argus:argus_secret@localhost:5432/argus",
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
