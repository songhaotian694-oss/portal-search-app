from __future__ import annotations
def chunk_text(text: str, size: int=500, overlap: int=80) -> list[str]:
    text="".join(text.split())
    if not text:return []
    out=[]; start=0
    while start<len(text):
        end=min(len(text),start+size)
        if end<len(text):
            pivot=max(text.rfind(x,start,end) for x in "。！？；")
            if pivot>start+size//2:end=pivot+1
        out.append(text[start:end]); start=max(end-overlap,start+1)
    return out
