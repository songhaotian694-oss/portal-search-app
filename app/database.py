from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Any
from .settings import DIRS, ensure_directories

def fts_terms(text: str) -> str:
    """FTS5 的 unicode61 不会自然分开连续汉字；按字拆开以支持中文关键词。"""
    import re
    return re.sub(r"([\u4e00-\u9fff])", r"\1 ", text).strip()

def now() -> str: return datetime.now().isoformat(timespec="seconds")

class Database:
    def __init__(self, path: Path | None = None):
        ensure_directories(); self.path = path or DIRS["database"] / "portal_search.db"; self.initialize()
    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path); con.row_factory = sqlite3.Row
        try: yield con; con.commit()
        finally: con.close()
    def initialize(self) -> None:
        with self.connection() as c:
            c.executescript('''
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS articles (
              id INTEGER PRIMARY KEY, portal_id TEXT, title TEXT NOT NULL, published_at TEXT, category TEXT,
              detail_url TEXT NOT NULL UNIQUE, raw_html_path TEXT, text_path TEXT, content_hash TEXT,
              download_status TEXT NOT NULL DEFAULT 'pending', collected_at TEXT, updated_at TEXT);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_portal_id ON articles(portal_id) WHERE portal_id IS NOT NULL;
            CREATE TABLE IF NOT EXISTS attachments (
              id INTEGER PRIMARY KEY, article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
              name TEXT, file_path TEXT, file_type TEXT, file_hash TEXT, parse_status TEXT DEFAULT 'pending', text_path TEXT,
              is_external INTEGER DEFAULT 0, UNIQUE(article_id, file_hash));
            CREATE TABLE IF NOT EXISTS extracted_records (
              id INTEGER PRIMARY KEY, article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
              graduation_year TEXT, grade TEXT, degree TEXT, major TEXT, city TEXT, employer TEXT, position TEXT,
              evidence_json TEXT NOT NULL DEFAULT '{}', needs_review INTEGER DEFAULT 1, reviewed INTEGER DEFAULT 0, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS experience_records (
              id INTEGER PRIMARY KEY, article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
              record_no INTEGER NOT NULL, student_name TEXT, graduation_year TEXT, grade TEXT, degree TEXT, major TEXT,
              city TEXT, employer TEXT, position TEXT, evidence_text TEXT,
              needs_review INTEGER DEFAULT 1, updated_at TEXT, UNIQUE(article_id,record_no));
            CREATE TABLE IF NOT EXISTS sync_jobs (
              id INTEGER PRIMARY KEY, started_at TEXT, ended_at TEXT, fetched_count INTEGER DEFAULT 0,
              success_count INTEGER DEFAULT 0, failure_count INTEGER DEFAULT 0, status TEXT, message TEXT);
            CREATE TABLE IF NOT EXISTS failures (
              id INTEGER PRIMARY KEY, job_id INTEGER REFERENCES sync_jobs(id), url TEXT, stage TEXT, error TEXT, retry_count INTEGER DEFAULT 0, resolved INTEGER DEFAULT 0, created_at TEXT);
            CREATE VIRTUAL TABLE IF NOT EXISTS article_fts USING fts5(article_id UNINDEXED, title, content);
            CREATE TABLE IF NOT EXISTS chunks (
              id INTEGER PRIMARY KEY, article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
              chunk_no INTEGER, text TEXT, vector_json TEXT);
            ''')
            columns={row[1] for row in c.execute("PRAGMA table_info(experience_records)")}
            if "student_name" not in columns:c.execute("ALTER TABLE experience_records ADD COLUMN student_name TEXT")
    def upsert_article(self, item: dict[str, Any]) -> tuple[int, bool]:
        with self.connection() as c:
            row = c.execute("SELECT id,content_hash FROM articles WHERE detail_url=?", (item["detail_url"],)).fetchone()
            vals = (item.get("portal_id"), item["title"], item.get("published_at"), item.get("category", "就业信息"), item["detail_url"], item.get("raw_html_path"), item.get("text_path"), item.get("content_hash"), item.get("download_status", "done"), now(), now())
            if row:
                c.execute('''UPDATE articles SET portal_id=?,title=?,published_at=?,category=?,raw_html_path=COALESCE(?,raw_html_path),text_path=COALESCE(?,text_path),content_hash=COALESCE(?,content_hash),download_status=?,updated_at=? WHERE id=?''', (item.get("portal_id"),item["title"],item.get("published_at"),item.get("category","就业信息"),item.get("raw_html_path"),item.get("text_path"),item.get("content_hash"),item.get("download_status","done"),now(),row["id"]))
                return row["id"], row["content_hash"] != item.get("content_hash")
            cur = c.execute("INSERT INTO articles(portal_id,title,published_at,category,detail_url,raw_html_path,text_path,content_hash,download_status,collected_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", vals)
            return int(cur.lastrowid), True
    def add_attachment(self, article_id: int, item: dict[str, Any]) -> None:
        with self.connection() as c:
            c.execute("INSERT OR IGNORE INTO attachments(article_id,name,file_path,file_type,file_hash,parse_status,text_path,is_external) VALUES(?,?,?,?,?,?,?,?)", (article_id,item.get("name"),item.get("file_path"),item.get("file_type"),item.get("file_hash"),item.get("parse_status","pending"),item.get("text_path"),int(item.get("is_external",False))))
    def create_job(self, message: str = "") -> int:
        with self.connection() as c: return int(c.execute("INSERT INTO sync_jobs(started_at,status,message) VALUES(?,?,?)", (now(),"running",message)).lastrowid)
    def finish_job(self, job_id: int, status: str, fetched: int, success: int, failed: int, message: str = "") -> None:
        with self.connection() as c: c.execute("UPDATE sync_jobs SET ended_at=?,status=?,fetched_count=?,success_count=?,failure_count=?,message=? WHERE id=?",(now(),status,fetched,success,failed,message,job_id))
    def add_failure(self, job_id: int | None, url: str, stage: str, error: str) -> None:
        with self.connection() as c: c.execute("INSERT INTO failures(job_id,url,stage,error,created_at) VALUES(?,?,?,?,?)",(job_id,url,stage,error[:1000],now()))
    def update_fts(self, article_id: int, title: str, content: str) -> None:
        with self.connection() as c:
            c.execute("DELETE FROM article_fts WHERE article_id=?", (article_id,)); c.execute("INSERT INTO article_fts(article_id,title,content) VALUES(?,?,?)", (article_id,fts_terms(title),fts_terms(content)))
    def replace_chunks(self, article_id: int, chunks: list[str], vectors: list[list[float] | None]) -> None:
        with self.connection() as c:
            c.execute("DELETE FROM chunks WHERE article_id=?",(article_id,))
            c.executemany("INSERT INTO chunks(article_id,chunk_no,text,vector_json) VALUES(?,?,?,?)", [(article_id,i,t,json.dumps(v) if v is not None else None) for i,(t,v) in enumerate(zip(chunks,vectors))])
    def save_record(self, article_id: int, data: dict[str, Any], reviewed: bool = False) -> None:
        evidence = json.dumps(data.get("evidence",{}),ensure_ascii=False)
        fields = [data.get(x,"待人工核对") for x in ["graduation_year","grade","degree","major","city","employer","position"]]
        needs = int(data.get("needs_review", True))
        with self.connection() as c: c.execute('''INSERT INTO extracted_records(article_id,graduation_year,grade,degree,major,city,employer,position,evidence_json,needs_review,reviewed,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(article_id) DO UPDATE SET graduation_year=excluded.graduation_year,grade=excluded.grade,degree=excluded.degree,major=excluded.major,city=excluded.city,employer=excluded.employer,position=excluded.position,evidence_json=excluded.evidence_json,needs_review=excluded.needs_review,reviewed=excluded.reviewed,updated_at=excluded.updated_at''',(article_id,*fields,evidence,needs,int(reviewed),now()))
    def update_attachment_parse(self, attachment_id:int, status:str, text_path:str|None) -> None:
        with self.connection() as c:c.execute("UPDATE attachments SET parse_status=?,text_path=? WHERE id=?",(status,text_path,attachment_id))
    def stats(self) -> dict[str, Any]:
        with self.connection() as c:
            one=lambda q: c.execute(q).fetchone()[0]
            last=c.execute("SELECT ended_at FROM sync_jobs WHERE status='completed' ORDER BY id DESC LIMIT 1").fetchone()
            return {"articles":one("SELECT count(*) FROM articles"),"processed":one("SELECT count(*) FROM extracted_records"),"valid_records":one("SELECT count(*) FROM experience_records"),"needs_review":one("SELECT count(*) FROM experience_records WHERE needs_review=1"),"last_sync": last[0] if last else None}
    def target_articles_to_process(self, all_local:bool) -> list[sqlite3.Row]:
        sql="""SELECT DISTINCT a.* FROM articles a LEFT JOIN experience_records e ON e.article_id=a.id
        LEFT JOIN attachments t ON t.article_id=a.id
        WHERE a.title LIKE '%选调%' AND a.title LIKE '%经验分享%'"""
        if not all_local:sql += " AND (e.id IS NULL OR t.parse_status IN ('pending','pending_ocr'))"
        sql += " ORDER BY a.id"
        with self.connection() as c:return c.execute(sql).fetchall()
    def replace_experience_records(self,article_id:int,records:list[dict[str,Any]])->None:
        fields=["student_name","graduation_year","grade","degree","major","city","employer","position"]
        with self.connection() as c:
            c.execute("DELETE FROM experience_records WHERE article_id=?",(article_id,))
            c.executemany("""INSERT INTO experience_records(article_id,record_no,student_name,graduation_year,grade,degree,major,city,employer,position,evidence_text,needs_review,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",[(article_id,i,*[r.get(k,"待人工核对") for k in fields],r.get("evidence_text",""),int(r.get("needs_review",True)),now()) for i,r in enumerate(records,1)])
    def experience_rows(self,limit:int=1000)->list[dict[str,Any]]:
        with self.connection() as c:return [dict(x) for x in c.execute("""SELECT e.*,a.title,a.published_at,a.detail_url,a.collected_at
        FROM experience_records e JOIN articles a ON a.id=e.article_id ORDER BY a.published_at DESC,e.record_no LIMIT ?""",(limit,))]
    def search_experience_rows(self,query:str="",filters:dict[str,str]|None=None,limit:int=50)->list[dict[str,Any]]:
        filters=filters or {}
        fields=["student_name","graduation_year","grade","degree","major","city","employer","position"]
        sql="""SELECT e.*,a.title,a.published_at,a.detail_url,a.collected_at
        FROM experience_records e JOIN articles a ON a.id=e.article_id WHERE 1=1"""
        args=[]
        def like(value:str)->str:
            return "%"+value.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")+"%"
        for word in query.split():
            sql+=" AND ("+" OR ".join(f"e.{field} LIKE ? ESCAPE '\\'" for field in fields)+" OR a.title LIKE ? ESCAPE '\\')"
            args.extend([like(word)]*(len(fields)+1))
        for field in ["graduation_year","degree","major","city"]:
            if filters.get(field):
                sql+=f" AND e.{field} LIKE ? ESCAPE '\\'";args.append(like(filters[field]))
        if filters.get("date_from"):
            sql+=" AND a.published_at>=?";args.append(filters["date_from"])
        if filters.get("date_to"):
            sql+=" AND a.published_at<=?";args.append(filters["date_to"])
        sql+=" ORDER BY a.published_at DESC,e.record_no LIMIT ?";args.append(limit)
        with self.connection() as c:return [dict(x) for x in c.execute(sql,args)]
    def experience_city_examples(self,limit:int=6)->list[str]:
        with self.connection() as c:
            return [row[0] for row in c.execute("""SELECT city FROM experience_records
                WHERE city IS NOT NULL AND city!='待人工核对' AND city NOT LIKE '%（省级单位）'
                GROUP BY city ORDER BY count(*) DESC,city LIMIT ?""",(limit,))]
    def articles_to_process(self, all_local: bool) -> list[sqlite3.Row]:
        with self.connection() as c: return c.execute("SELECT a.* FROM articles a " + ("" if all_local else "LEFT JOIN extracted_records r ON r.article_id=a.id WHERE r.id IS NULL") + " ORDER BY a.id").fetchall()
    def get_article(self, article_id: int) -> dict[str, Any] | None:
        with self.connection() as c:
            a=c.execute("SELECT a.*,r.* FROM articles a LEFT JOIN extracted_records r ON r.article_id=a.id WHERE a.id=?",(article_id,)).fetchone()
            if not a:return None
            d=dict(a); d["evidence"]=json.loads(d.pop("evidence_json") or "{}")
            d["attachments"]=[dict(x) for x in c.execute("SELECT * FROM attachments WHERE article_id=?",(article_id,))]
            return d
    def review_article(self, article_id: int, fields: dict[str, Any]) -> None:
        old=self.get_article(article_id) or {}; evidence=json.loads(old.get("evidence_json") or "{}") if old else {}
        data={k: fields.get(k) if fields.get(k) is not None else old.get(k,"待人工核对") for k in ["graduation_year","grade","degree","major","city","employer","position"]}; data["evidence"] = evidence; data["needs_review"] = fields.get("needs_review",False); self.save_record(article_id,data,True)
    def all_rows(self, filters: dict[str,str] | None=None) -> list[dict[str,Any]]:
        filters=filters or {}; sql="SELECT a.*,r.* FROM articles a LEFT JOIN extracted_records r ON r.article_id=a.id WHERE 1=1"; args=[]
        for key in ["graduation_year","degree","major","city"]:
            if filters.get(key):sql += f" AND r.{key} LIKE ?";args.append("%"+filters[key]+"%")
        if filters.get("date_from"):sql += " AND a.published_at>=?";args.append(filters["date_from"])
        if filters.get("date_to"):sql += " AND a.published_at<=?";args.append(filters["date_to"])
        with self.connection() as c:return [dict(x) for x in c.execute(sql,args)]

db = Database()
