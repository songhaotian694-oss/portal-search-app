from __future__ import annotations
from pathlib import Path
import pymupdf
from docx import Document
from openpyxl import load_workbook

_ocr_engine=None

def image_ocr(path:Path)->str:
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine=RapidOCR()
    result,_=_ocr_engine(str(path))
    return "\n".join(item[1] for item in (result or []) if len(item)>1 and item[1])

def extract_attachment_text(path: Path) -> tuple[str, str]:
    """返回附件文字和状态；就业分享海报在本机使用中文OCR识别。"""
    try:
        ext=path.suffix.lower()
        if ext==".pdf":
            doc=pymupdf.open(path); text="\n".join(page.get_text() for page in doc)
            return (text, "parsed" if text.strip() else "pending_ocr")
        if ext==".docx":
            doc=Document(path); rows=[]
            for p in doc.paragraphs: rows.append(p.text)
            for table in doc.tables:
                rows.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
            return "\n".join(rows),"parsed"
        if ext in {".xlsx",".xlsm"}:
            wb=load_workbook(path,data_only=True,read_only=True); rows=[]
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True): rows.append(" | ".join(str(x) for x in row if x is not None))
            return "\n".join(rows),"parsed"
        if ext in {".png",".jpg",".jpeg",".bmp",".tiff"}:
            text=image_ocr(path)
            return text,("ocr_parsed" if text.strip() else "ocr_empty")
        return "","unsupported"
    except Exception as exc: return f"[附件解析失败：{type(exc).__name__}]","failed"
