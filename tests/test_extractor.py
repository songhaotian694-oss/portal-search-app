from pathlib import Path
import pytest
from app.processing.html_parser import parse_list_page,has_next_page,clean_html,extract_attachments
from app.processing.field_extractor import extract_fields
from app.processing.attachment_parser import extract_attachment_text
FIX=Path(__file__).parent/"fixtures"
CFG={"list_item_selector":".item","title_selector":".title","date_selector":".date","detail_link_selector":".title","next_button_selector":".next","detail_body_selector":".article-body","attachment_selector":".attachment"}
def test_list_body_and_attachments():
    items=parse_list_page((FIX/"list.html").read_text(encoding="utf-8"),"https://mock.local/",CFG)
    assert len(items)==2 and items[0]["portal_id"]=="mock-001" and has_next_page((FIX/"list.html").read_text(encoding="utf-8"),CFG)
    html=(FIX/"detail-001.html").read_text(encoding="utf-8");text=clean_html(html,".article-body")
    assert "门户导航" not in text and "基层公务员" in text
    assert extract_attachments(html,"https://mock.local/x/",".attachment")[0]["url"].endswith("resume-001.docx")
    image_html='<div class="content"><img alt="通知图片.jpg" src="/upload/notice.jpg"></div>'
    image=extract_attachments(image_html,"https://mock.local/detail",".content img[src]")[0]
    assert image=={"url":"https://mock.local/upload/notice.jpg","name":"通知图片.jpg"}
@pytest.mark.parametrize("text, expected",[
 ("我是2024届、2020级本科生，软件工程专业，在北京。","2024届"),("2023届硕士研究生，计算机科学与技术专业，在深圳入职。","硕士"),("2022届博士毕业生，民族学专业，去拉萨任职。","博士"),("2025届本科毕业生，法学专业，成都岗位。","本科"),("2021级同学为2025届，金融学，上海。","2025届"),("2020届硕士毕业生，公共管理专业，在天津。","硕士"),("2024届本科生，电子信息工程专业，武汉录用。","本科"),("2023届博士研究生，统计学专业，杭州。","博士"),("2022届本科生，新闻学专业，广州。","本科"),("2021届硕士研究生，教育学专业，西安。","硕士"),("2024届本科毕业生，人工智能专业，北京。","本科"),("2023届硕士毕业生，行政管理专业，郑州。","硕士"),("2022届博士生，社会学专业，昆明。","博士"),("2020级2024届本科生，数学与应用数学专业，南京。","2024届"),("2024届硕士研究生，心理学专业，长沙。","硕士"),("2023届本科生，英语专业，厦门。","本科"),("2022届博士研究生，经济学专业，济南。","博士"),("2021届本科毕业生，通信工程专业，青岛。","本科"),("2024届硕士毕业生，数据科学与大数据技术专业，福州。","硕士"),("2025届本科生，工商管理专业，重庆。","本科")])
def test_twenty_chinese_field_cases(text,expected):
    d=extract_fields(text);assert expected in " ".join(str(v) for v in d.values())
def test_unit_position_evidence_is_not_guessed():
    d=extract_fields("2024届本科生，软件工程专业，北京。通过考试被北京市某区组织部录用，岗位为基层公务员。")
    assert "组织部" in d["evidence"]["employer"]["sentence"] and d["position"] != "待人工核对"
def test_docx_attachment(tmp_path):
    from docx import Document
    p=tmp_path/"a.docx";doc=Document();doc.add_paragraph("2024届软件工程 北京");doc.save(p)
    text,status=extract_attachment_text(p);assert status=="parsed" and "软件工程" in text
