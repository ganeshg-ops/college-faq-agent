import os
import re
import math
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

from config import (
    DOCUMENTS_DIR,
    TOP_K_RESULTS,
    MIN_RELEVANCE_SCORE,
    ALLOWED_EXTENSIONS,
)
from document_processor import DocumentProcessor, DocumentProcessingError


STOP_WORDS = {
    "what", "is", "the", "a", "an", "and", "or", "of", "to", "in", "on", "at",
    "for", "with", "about", "are", "do", "does", "did", "can", "could", "should",
    "would", "how", "when", "where", "which", "who", "whom", "whose", "why",
    "it", "this", "that", "these", "those", "i", "you", "he", "she", "we", "they",
    "me", "my", "your", "our", "their", "be", "been", "being", "have", "has", "had",
    "any", "some", "all", "so", "there", "here", "as", "by", "from", "tell", "give", "please"
}


def tokenize(text: str) -> List[str]:
    """
    Tokenizes multilingual text (English, Tamil, numbers) into lowercase terms.
    Preserves Tamil Unicode characters (U+0B80 to U+0BFF).
    """
    tokens = re.findall(r"[\w\u0b80-\u0bff]+", text.lower(), re.UNICODE)
    return tokens


class BM25SearchEngine:
    """
    Pure-Python Okapi BM25 ranking engine with section/title weighting,
    stop-word suppression, and normalized scoring for threshold-based relevance verification.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[Dict[str, Any]] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_lens: List[int] = []
        self.avg_dl: float = 0.0
        self.doc_freqs: Dict[str, int] = Counter()
        self.num_docs: int = 0
        self.idf: Dict[str, float] = {}

    def fit(self, chunks: List[Dict[str, Any]]) -> None:
        """Indexes a list of document chunks for fast retrieval."""
        self.chunks = chunks
        self.num_docs = len(chunks)
        self.doc_tokens = []
        self.doc_lens = []
        self.doc_freqs = Counter()

        if self.num_docs == 0:
            self.avg_dl = 0.0
            self.idf = {}
            return

        total_len = 0
        for chunk in chunks:
            # Combine section title (given extra weight) with chunk body
            section = chunk.get("section", "")
            combined_text = f"{section} {section} {chunk.get('text', '')}"
            tokens = tokenize(combined_text)
            self.doc_tokens.append(tokens)
            doc_len = len(tokens)
            self.doc_lens.append(doc_len)
            total_len += doc_len

            unique_terms = set(tokens)
            for term in unique_terms:
                self.doc_freqs[term] += 1

        self.avg_dl = total_len / self.num_docs if self.num_docs > 0 else 0.0

        # Calculate BM25 IDF for all terms
        self.idf = {}
        for term, freq in self.doc_freqs.items():
            idf_val = math.log((self.num_docs - freq + 0.5) / (freq + 0.5) + 1.0)
            self.idf[term] = max(0.01, idf_val)

    def search(self, query: str, top_k: int = TOP_K_RESULTS) -> List[Tuple[Dict[str, Any], float]]:
        """
        Calculates BM25 score for the query across all chunks.
        Suppresses common stop-words and requires informative token matching.
        Returns top_k tuples of (chunk_dict, normalized_score).
        """
        if self.num_docs == 0:
            return []

        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        # Filter informative tokens
        informative_tokens = [t for t in q_tokens if t not in STOP_WORDS and len(t) > 1]
        active_tokens = informative_tokens if informative_tokens else q_tokens

        # Check if at least some active tokens exist in vocabulary
        known_active_tokens = [t for t in active_tokens if t in self.idf]
        if not known_active_tokens:
            return []

        scores = [0.0] * self.num_docs
        matched_informative_count = [0] * self.num_docs
        query_freqs = Counter(active_tokens)

        for term, q_tf in query_freqs.items():
            if term not in self.idf:
                continue
            term_idf = self.idf[term]

            for i, tokens in enumerate(self.doc_tokens):
                tf = tokens.count(term)
                if tf == 0:
                    continue
                matched_informative_count[i] += 1
                doc_len = self.doc_lens[i]
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_dl))
                numerator = tf * (self.k1 + 1.0)
                term_score = term_idf * (numerator / denom)
                scores[i] += term_score

        # Also check term coverage for multi-concept queries
        unique_active_terms = len(query_freqs)
        query_lower = query.lower().strip()
        for i, chunk in enumerate(self.chunks):
            # If chunk didn't match any informative tokens, nullify its score
            if matched_informative_count[i] == 0:
                scores[i] = 0.0
                continue

            # If query has 3 or more distinct informative concepts, require at least 2 distinct concept matches
            coverage = matched_informative_count[i] / unique_active_terms
            if unique_active_terms >= 3 and (matched_informative_count[i] < 2 or coverage < 0.35):
                scores[i] = 0.0
                continue

            chunk_text = chunk.get("text", "").lower()
            if len(query_lower) > 5 and query_lower in chunk_text:
                scores[i] *= 1.3

        # Rank documents
        scored_pairs = list(enumerate(scores))
        scored_pairs.sort(key=lambda x: x[1], reverse=True)

        # Normalize scores to 0.0 - 1.0 relative to max theoretical score of active tokens
        max_possible_score = sum(self.idf.get(t, 1.0) * (self.k1 + 1.0) for t in active_tokens)
        max_possible_score = max(max_possible_score, 1.0)

        results = []
        for idx, raw_score in scored_pairs[:top_k]:
            if raw_score <= 0.0:
                continue
            normalized = min(1.0, raw_score / max_possible_score)
            results.append((self.chunks[idx], round(normalized, 4)))

        return results


class DocumentSearchManager:
    """
    Manages indexing and searching approved college documents stored in `DOCUMENTS_DIR`.
    Provides persistence, live re-indexing, document statistics, and retrieval.
    """

    def __init__(self, documents_dir: Path = DOCUMENTS_DIR):
        self.documents_dir = Path(documents_dir)
        self.processor = DocumentProcessor()
        self.engine = BM25SearchEngine()
        self.chunks: List[Dict[str, Any]] = []
        self.document_stats: Dict[str, Dict[str, Any]] = {}
        self.load_and_index_all()

    def load_and_index_all(self) -> int:
        """
        Scans DOCUMENTS_DIR, extracts text from all approved documents,
        and builds the BM25 index. Returns total chunk count.
        """
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        all_chunks = []
        stats = {}

        for file_path in self.documents_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue

            try:
                file_chunks = self.processor.process_file(file_path)
                all_chunks.extend(file_chunks)
                stats[file_path.name] = {
                    "chunks": len(file_chunks),
                    "size_kb": round(file_path.stat().st_size / 1024, 1),
                    "file_type": file_path.suffix.upper().lstrip("."),
                    "status": "indexed",
                }
            except Exception as e:
                stats[file_path.name] = {
                    "chunks": 0,
                    "size_kb": round(file_path.stat().st_size / 1024, 1),
                    "file_type": file_path.suffix.upper().lstrip("."),
                    "status": f"error: {str(e)}",
                }

        self.chunks = all_chunks
        self.document_stats = stats
        self.engine.fit(self.chunks)
        return len(self.chunks)

    def search_documents(
        self, query: str, top_k: int = TOP_K_RESULTS, min_score: float = MIN_RELEVANCE_SCORE
    ) -> Dict[str, Any]:
        """
        Executes query retrieval over approved documents.
        Returns a dictionary with:
          - has_match: bool (True if highest score >= min_score)
          - top_score: float
          - results: list of {chunk, score}
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            return {"has_match": False, "top_score": 0.0, "results": []}

        scored_results = self.engine.search(cleaned_query, top_k=top_k)

        if not scored_results:
            return {"has_match": False, "top_score": 0.0, "results": []}

        top_score = scored_results[0][1]
        has_match = top_score >= min_score

        formatted_results = []
        for chunk, score in scored_results:
            formatted_results.append({
                "chunk_id": chunk["chunk_id"],
                "document_name": chunk["document_name"],
                "page": chunk.get("page"),
                "section": chunk.get("section"),
                "text": chunk["text"],
                "relevance_score": score,
            })

        return {
            "has_match": has_match,
            "top_score": top_score,
            "results": formatted_results,
        }

    def get_document_list(self) -> List[Dict[str, Any]]:
        """Returns metadata for all documents in the approved repository."""
        doc_list = []
        for name, info in self.document_stats.items():
            doc_list.append({
                "name": name,
                "type": info["file_type"],
                "size_kb": info["size_kb"],
                "chunks": info["chunks"],
                "status": info["status"],
            })
        return doc_list

    def delete_document(self, filename: str) -> bool:
        """Deletes a document from the approved repository and rebuilds index."""
        # Prevent directory traversal
        safe_name = Path(filename).name
        target_path = self.documents_dir / safe_name
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            self.load_and_index_all()
            return True
        return False
