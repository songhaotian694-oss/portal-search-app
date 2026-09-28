from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .settings import ensure_directories,ROOT
from .database import db
from .version import APP_VERSION
from .api import auth,sync,process,search,articles,export,settings,records
@asynccontextmanager
async def lifespan(app:FastAPI):
    ensure_directories();db.initialize();yield
app=FastAPI(title="就业分享信息检索",lifespan=lifespan)
for r in [auth.router,sync.router,process.router,search.router,articles.router,export.router,settings.router,records.router]:app.include_router(r)
@app.get("/api/dashboard")
async def dashboard():return db.stats()
@app.get("/api/version")
async def version():return {"version":APP_VERSION}
app.mount("/",StaticFiles(directory=ROOT/"app"/"static",html=True),name="static")
