from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .settings import ensure_directories, RESOURCE_ROOT
from .database import db
from .version import APP_VERSION
from .api import auth,sync,process,search,articles,export,settings,records,analytics
@asynccontextmanager
async def lifespan(app:FastAPI):
    ensure_directories();db.initialize()
    try:
        yield
    finally:
        await auth.browser_session.close()
app=FastAPI(title="就业分享信息检索",lifespan=lifespan)
for r in [auth.router,sync.router,process.router,search.router,articles.router,export.router,settings.router,records.router,analytics.router]:app.include_router(r)
@app.get("/api/dashboard")
async def dashboard():return db.stats()
@app.get("/api/version")
async def version():return {"version":APP_VERSION}
frontend_dir=RESOURCE_ROOT/"frontend"/"dist"
app.mount("/assets",StaticFiles(directory=frontend_dir/"assets"),name="frontend-assets")

@app.get("/")
@app.get("/search")
@app.get("/explore")
@app.get("/workspace")
async def frontend():return FileResponse(frontend_dir/"index.html")
