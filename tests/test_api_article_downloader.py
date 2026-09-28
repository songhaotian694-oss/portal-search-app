import asyncio

from app.crawler import article_downloader


class FakeResponse:
    status = 200
    headers = {"content-type": "image/png"}

    async def body(self):
        return b"fake-png"


class FakeRequest:
    async def get(self, url):
        assert url == "https://my.muc.edu.cn/files/photo.png"
        return FakeResponse()


class FakePage:
    # 故意不提供 goto：证明接口正文保存不依赖打开详情页。
    request = FakeRequest()


def test_save_api_article_without_opening_detail_page(tmp_path, monkeypatch):
    dirs = {"raw_html": tmp_path / "html", "article_text": tmp_path / "text", "attachments": tmp_path / "attachments"}
    for path in dirs.values():
        path.mkdir()
    monkeypatch.setattr(article_downloader, "DIRS", dirs)
    item = {
        "portal_id": "1", "title": "选调经验分享", "published_at": "2026-01-01",
        "detail_url": "https://my.muc.edu.cn/page/11#/print?notice_id=1", "category": "就业信息",
    }
    row = {"notice_content": "<p>正文内容</p><img src='/files/photo.png'>"}
    saved, attachments = asyncio.run(article_downloader.save_api_article(
        FakePage(), item, row, {"allowed_domains": ["my.muc.edu.cn"]}
    ))
    assert "正文内容" in next((tmp_path / "text").glob("*.txt")).read_text(encoding="utf-8")
    assert saved["download_status"] == "done"
    assert len(attachments) == 1
