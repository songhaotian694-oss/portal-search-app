import asyncio,json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.database import Database
from app.processing.field_extractor import extract_experience_records,PIPELINE_VERSION,validate_ocr_record


def test_status_anchors_reject_slogan_and_rejoin_wrapped_jobs():
    text='''秋招扬帆·你我同行
12月22日19点
王同学
贵州省2022年定向选调生
理学院2018级纳米材料与技术专
业本科生
贵州省黔南布依族苗族自治州长顺
县乡村振兴局试用期公务员（不定
职级）
李同学
米
贵州省2022年定向选调生
法学院2019级法律（非法学）专
业硕士研究生
贵州省兴义市人民检察院试用期公
务员（不定职级）
扫码关注我们'''
    rows=extract_experience_records(text,'贵州定向选调经验分享')
    assert [r['student_name'] for r in rows]==['王同学','李同学']
    assert rows[0]['employer'].endswith('长顺县乡村振兴局')
    assert rows[1]['position']=='试用期公务员（不定职级）'
    assert rows[0]['graduation_year']=='待人工核对'  # Never invent graduation from selection year.
    assert rows[0]['quality']['missing_fields']==['graduation_year']


def test_second_degree_and_explicit_district_are_preserved():
    rows=extract_experience_records('张同学\n2023届定向选调生\n法学院2021级法学第二学士学位毕业生\n乌当区自然资源局\n试用期公务员（不定职级）','贵州选调经验分享')
    assert rows[0]['degree']=='第二学士学位毕业生'
    assert rows[0]['major']=='法学'
    assert rows[0]['city']=='乌当区'


def test_older_poster_without_grade_retains_actual_major_and_people():
    text='王同学\n2022届新闻与传播学院\n新闻与传播专业毕业生\n现就职于沧州市委党校\n李同学\n2022届民族学与社会学学院\n民族学（孝通班）专业毕业生\n现就职于石家庄市总工会\n扫码关注我们'
    rows=extract_experience_records(text,'河北选调经验分享')
    assert len(rows)==2
    assert rows[0]['major']=='新闻与传播' and rows[0]['city']=='沧州市'
    assert rows[1]['major']=='民族学（孝通班）'
    assert rows[0]['degree']=='待人工核对'  # 学院/研究生会 must never imply degree.


def test_education_before_wrapped_selection_status_is_associated_with_name():
    text='校友介绍\n王同学\n信息工程学院2021级研究生、2017\n级本科生\n2024年山东省威海市纪委监委派驻\n纪检监察组选调生\n扫码关注我们'
    rows=extract_experience_records(text,'山东选调经验分享')
    assert len(rows)==1 and rows[0]['student_name']=='王同学'
    assert rows[0]['grade']=='2021级、2017级'
    assert rows[0]['city']=='山东省威海市'


def test_unreliable_ocr_field_is_withheld_after_retry():
    text='王同学\n2024届选调生\n学院2020级法学专业本科生\n北京市财政局\n公务员'
    record=extract_experience_records(text,'选调经验分享')[0]
    proof=[{'text':line,'score':.65 if line=='北京市财政局' else .99} for line in text.splitlines()]
    result=validate_ocr_record(record,proof)
    assert result['employer']=='待人工核对' and result['city']=='待人工核对'
    assert set(result['quality']['withheld_fields'])=={'employer','city'}
    assert result['major']=='法学'


def test_failed_attachment_does_not_destroy_previous_success(tmp_path,monkeypatch):
    from app.api import process
    d=Database(tmp_path/'preserve.db')
    aid,_=d.upsert_article({'title':'选调经验分享','detail_url':'https://test.local/keep'})
    d.replace_experience_records(aid,[{'student_name':'王同学','needs_review':True}])
    d.add_attachment(aid,{'file_path':str(tmp_path/'missing.jpg'),'file_hash':'bad','file_type':'.jpg'})
    monkeypatch.setattr(process,'db',d)
    monkeypatch.setattr(process,'extract_attachment_text',lambda _: ('[failed]','failed'))
    monkeypatch.setattr(process,'STATE',{'status':'idle','current':0,'total':0,'message':''})
    from app.models import ProcessRequest
    asyncio.run(process.run(ProcessRequest(all_local=True,build_index=False)))
    assert d.experience_rows()[0]['student_name']=='王同学'
    assert process.STATE['failed']==1 and d.metadata('pipeline_version') is None


@pytest.mark.parametrize('existing,current,stage',[(False,False,'sync'),(True,False,'process'),(True,True,None)])
def test_first_login_fetches_or_upgrades_once(tmp_path,monkeypatch,existing,current,stage):
    from app.api import sync,process
    d=Database(tmp_path/'fresh.db')
    if existing:d.upsert_article({'title':'选调经验分享','detail_url':'https://test.local/1'})
    if current:d.set_metadata('pipeline_version',PIPELINE_VERSION)
    calls=[]
    async def authenticated():return True,''
    async def start_sync(req):calls.append(('sync',req.mode,req.max_pages))
    async def start_process(req):calls.append(('process',req.all_local))
    monkeypatch.setattr(sync,'db',d);monkeypatch.setattr(sync,'_ensured',False)
    monkeypatch.setattr(sync,'task',None);monkeypatch.setattr(process,'task',None)
    monkeypatch.setattr(sync.browser_session,'is_logged_in',authenticated)
    monkeypatch.setattr(sync,'start',start_sync);monkeypatch.setattr(process,'start',start_process)
    async def check():
        first=await sync.ensure();second=await sync.ensure()
        assert first.get('stage')==stage and not second['started']
    asyncio.run(check())
    assert len(calls)==(1 if stage else 0)
    if stage=='sync':assert calls[0]==('sync','full',1000)


def test_scanned_pdf_is_ocr_processed(tmp_path,monkeypatch):
    import pymupdf
    from app.processing import attachment_parser as parser
    path=tmp_path/'scan.pdf'
    with pymupdf.open() as doc:
        doc.new_page();doc.save(path)
    monkeypatch.setattr(parser,'_ocr_rows',lambda _: [{'text':'2024届本科生','box':[],'score':.99}])
    text,status=parser.extract_attachment_text(path)
    assert text=='2024届本科生' and status=='ocr_parsed'


def test_ocr_retry_merges_lines_and_reuses_hash_cache(tmp_path,monkeypatch):
    import numpy as np,cv2
    from app.processing import attachment_parser as parser
    path=tmp_path/'sample.png';cv2.imwrite(str(path),np.zeros((800,400,3),np.uint8))
    calls=[]
    def recognize(_):
        calls.append(1)
        return [{'box':[[10,10],[150,10],[150,30],[10,30]],'text':'2024届本科生','score':.75 if len(calls)==1 else .99}]
    monkeypatch.setattr(parser,'_ocr_rows',recognize)
    result=parser.image_ocr_details(path)
    assert result['passes']==3 and max(r['score'] for r in result['lines'])==.99
    assert parser.image_ocr_details(path)==result and len(calls)==3
    assert result['version']==parser.OCR_VERSION


def test_fresh_machine_uses_public_profile_without_local_secrets(tmp_path,monkeypatch):
    from app import settings
    monkeypatch.setattr(settings,'CONFIG_DIR',tmp_path)
    cfg=settings.load_config()
    assert cfg['portal_url'].startswith('https://ca.muc.edu.cn/')
    assert cfg['data_source']=='api'
    assert not any(key.lower() in {'cookie','password','token','authorization'} for key in cfg)
