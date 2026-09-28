from app.database import Database
from app.settings import safe_filename,is_allowed_url
def test_dedupe_increment_and_paths(tmp_path):
    d=Database(tmp_path/"x.db");item={"title":"文章","detail_url":"https://portal.example.edu/a","content_hash":"1"}
    a,new=d.upsert_article(item);b,changed=d.upsert_article(item);assert a==b and new and not changed
    item["content_hash"]="2";_,changed=d.upsert_article(item);assert changed
    assert safe_filename("../../a<bad>.pdf")=="a_bad_.pdf"
    assert is_allowed_url("https://sub.muc.edu.cn/x",{"allowed_domains":["muc.edu.cn"]}) and not is_allowed_url("https://evil.com",{"allowed_domains":["muc.edu.cn"]})
def test_failure_does_not_stop_other_records(tmp_path):
    d=Database(tmp_path/"x.db");job=d.create_job();d.add_failure(job,"u","download","bad")
    d.upsert_article({"title":"仍可保存","detail_url":"https://x/a","content_hash":"x"});assert d.stats()["articles"]==1
