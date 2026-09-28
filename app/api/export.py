from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from fastapi import APIRouter
from fastapi.responses import FileResponse
from openpyxl import Workbook
from ..database import db
from ..settings import DIRS
router=APIRouter(prefix="/api/export",tags=["导出"])
@router.get("")
async def export(graduation_year:str="",degree:str="",major:str="",city:str="",date_from:str="",date_to:str=""):
    rows=db.experience_rows();wb=Workbook();ws=wb.active;ws.title="检索结果"
    headers=["来源文章","发布时间","姓名","届别","年级","学历","专业","城市","就业单位","岗位","OCR证据文字","原文链接","提取状态","采集时间"]
    ws.append(headers)
    for r in rows:
        ws.append([r.get("title"),r.get("published_at"),r.get("student_name"),r.get("graduation_year"),r.get("grade"),r.get("degree"),r.get("major"),r.get("city"),r.get("employer"),r.get("position"),r.get("evidence_text"),r.get("detail_url"),"待人工核对" if r.get("needs_review") else "字段较完整",r.get("collected_at")])
    for name,headers,sql in [
        ("采集失败记录",["链接","阶段","错误","时间"],"SELECT url,stage,error,created_at FROM failures WHERE resolved=0"),
        ("待人工核对记录",["来源文章","姓名","届别","专业","岗位","原文链接"],
         "SELECT a.title,e.student_name,e.graduation_year,e.major,e.position,a.detail_url FROM experience_records e JOIN articles a ON a.id=e.article_id WHERE e.needs_review=1")]:
        s=wb.create_sheet(name);s.append(headers)
        with db.connection() as c:
            for x in c.execute(sql):s.append(list(x))
    for sheet in wb.worksheets:
        sheet.freeze_panes="A2";sheet.auto_filter.ref=sheet.dimensions
        for col in sheet.columns: sheet.column_dimensions[col[0].column_letter].width=min(45,max(12,max(len(str(x.value or "")) for x in col)+2))
    path=DIRS["exports"]/("就业检索导出_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".xlsx");wb.save(path)
    return FileResponse(path,filename=path.name,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
