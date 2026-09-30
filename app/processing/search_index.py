"""Local text chunks; indexing never downloads or loads an embedding model."""
from __future__ import annotations
from .text_chunker import chunk_text
from ..database import db


class SearchIndex:
    def index_article(self, article_id: int, text: str) -> None:
        chunks = chunk_text(text)
        db.replace_chunks(article_id, chunks, [None] * len(chunks))


search_index = SearchIndex()
