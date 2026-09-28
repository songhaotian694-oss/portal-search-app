from __future__ import annotations
import json
import numpy as np
from .text_chunker import chunk_text
from ..database import db

class SearchIndex:
    def __init__(self): self.model=None; self.error=None
    def _model(self):
        if self.model is not None:return self.model
        try:
            from sentence_transformers import SentenceTransformer
            self.model=SentenceTransformer("BAAI/bge-small-zh-v1.5")
        except Exception as e: self.error=f"语义模型不可用：{type(e).__name__}"; return None
        return self.model
    def index_article(self, article_id:int, text:str) -> None:
        chunks=chunk_text(text); model=self._model(); vectors=[]
        if model and chunks:
            vectors=[v.tolist() for v in model.encode(chunks,normalize_embeddings=True,show_progress_bar=False)]
        else:vectors=[None]*len(chunks)
        db.replace_chunks(article_id,chunks,vectors)
    def semantic(self, query:str, limit:int=40) -> dict[int,tuple[float,str]]:
        model=self._model()
        if not model:return {}
        q=model.encode([query],normalize_embeddings=True,show_progress_bar=False)[0]
        with db.connection() as c: rows=c.execute("SELECT article_id,text,vector_json FROM chunks WHERE vector_json IS NOT NULL").fetchall()
        best={}
        for r in rows:
            score=float(np.dot(q,np.array(json.loads(r["vector_json"]))))
            if r["article_id"] not in best or score>best[r["article_id"]][0]:best[r["article_id"]]=(score,r["text"])
        return dict(sorted(best.items(),key=lambda x:x[1][0],reverse=True)[:limit])
search_index=SearchIndex()
