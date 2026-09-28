import json

from app.crawler.portal_api import _parse_request_body, extract_rows, normalize_notice, prepare_body


def test_prepare_body_updates_nested_page_and_keyword():
    template = {
        "body_format": "json",
        "body": {"query": {"currentPage": 1, "pageSize": 15, "searchContent": ""}},
    }
    body, page_found, keyword_found = prepare_body(template, 2, "选调经验")
    value = json.loads(body)
    assert page_found and keyword_found
    assert value["query"]["currentPage"] == 3
    assert value["query"]["searchContent"] == "选调经验"


def test_extract_and_normalize_notice():
    result = {"datas": {"tables": [{
        "notice_id": 358652,
        "notice_title": "选调经验分享",
        "publish_time": "2026-09-12 17:28",
        "notice_type_id": 10,
    }]}}
    row = extract_rows(result)[0]
    item = normalize_notice(row, {
        "api_detail_url_template": "https://my.muc.edu.cn/print?id={notice_id}&type={notice_type}",
        "api_notice_type": 10,
    })
    assert item["portal_id"] == "358652"
    assert item["title"] == "选调经验分享"
    assert item["detail_url"].endswith("id=358652&type=10")


def test_prepare_form_body():
    template = {"body_format": "form", "body": {"pageNum": "0", "keyword": ""}}
    body, page_found, keyword_found = prepare_body(template, 1, "选调")
    assert page_found and keyword_found
    assert "pageNum=1" in body and "%E9%80%89%E8%B0%83" in body


def test_prepare_body_can_force_first_page_after_capturing_page_two():
    template = {"body_format": "form", "body": {"currentPage": "2", "searchValue": ""}}
    body, page_found, keyword_found = prepare_body(template, 0, "选调经验", absolute_page=1)
    assert page_found and keyword_found
    assert "currentPage=1" in body


def test_form_request_is_not_mislabeled_as_json():
    class Request:
        headers = {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"}
        post_data = "pageNum=0&keyword="
        post_data_json = {"pageNum": "0", "keyword": ""}

    body, body_format = _parse_request_body(Request())
    assert body_format == "form" and body["pageNum"] == "0"
