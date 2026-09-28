import asyncio

from app.database import Database
from app.api import search as search_api


def test_search_returns_students_instead_of_articles(tmp_path, monkeypatch):
    db = Database(tmp_path / "search.db")
    aid, _ = db.upsert_article({"title": "河北选调经验分享", "detail_url": "https://example.test/one", "published_at": "2024-10-01"})
    db.replace_experience_records(aid, [
        {"student_name": "张同学", "graduation_year": "2024届", "grade": "2020级", "degree": "本科生", "major": "计算机科学", "city": "保定市", "employer": "保定市财政局", "position": "公务员", "needs_review": False},
        {"student_name": "李同学", "graduation_year": "2023届", "grade": "2019级", "degree": "硕士生", "major": "法学", "city": "唐山市", "employer": "唐山市法院", "position": "公务员", "needs_review": False},
    ])
    db.upsert_article({"title": "北京选调经验模拟文章", "detail_url": "https://mock.local/beijing"})
    monkeypatch.setattr(search_api, "db", db)
    result = asyncio.run(search_api.search(q="张同学 财政局", limit=100))
    assert [r["student_name"] for r in result["results"]] == ["张同学"]
    assert result["results"][0]["employer"] == "保定市财政局"
    assert result["total_records"] == 2
    missing = asyncio.run(search_api.search(q="北京", limit=100))
    assert missing["results"] == []
    assert "保定市" in missing["city_examples"]


def test_student_search_filters_and_literal_wildcards(tmp_path):
    db = Database(tmp_path / "search.db")
    aid, _ = db.upsert_article({"title": "选调经验分享", "detail_url": "https://example.test/one"})
    db.replace_experience_records(aid, [
        {"student_name": "王甲", "graduation_year": "2024届", "grade": "2020级", "degree": "本科生", "major": "计算机科学", "city": "保定市", "employer": "某单位", "position": "科员"},
        {"student_name": "王乙", "graduation_year": "2024届", "grade": "2020级", "degree": "硕士生", "major": "法学", "city": "天津市", "employer": "某单位", "position": "科员"},
    ])
    assert [r["student_name"] for r in db.search_experience_rows("王", {"degree": "本科", "city": "保定"})] == ["王甲"]
    assert db.search_experience_rows("%") == []
