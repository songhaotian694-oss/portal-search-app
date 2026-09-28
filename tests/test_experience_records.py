from app.processing.field_extractor import extract_experience_records,is_experience_share,shared_image_relevant


def test_only_selection_experience_shares_are_target_data():
    assert is_experience_share("湖南选调经验分享")
    assert not is_experience_share("公务员考试讲座")


def test_one_poster_can_create_multiple_student_records():
    text="""余漆冰
2024届湖南选调生
民族学与社会学学院2021级文物与博物馆专业硕士研究生
湖南省株洲市炎陵县鹿原镇三口村
党总支书记助理（不定职级）
2024届湖南选调生
中国少数民族语言文学学院2021级中国少数民族语言文学专业硕士研究生
湖南省邵阳市双清区高崇山镇马杨村
党总支书记助理（不定职级）"""
    rows=extract_experience_records(text,"湖南选调经验分享")
    assert len(rows)==2
    assert rows[0]["student_name"]=="余漆冰"
    assert rows[0]["graduation_year"]=="2024届"
    assert rows[0]["grade"]=="2021级"
    assert rows[0]["degree"].startswith("硕士")
    assert "文物与博物馆" in rows[0]["major"]
    assert "株洲市" in rows[0]["city"]
    assert "书记助理" in rows[0]["position"]


def test_student_status_is_not_mistaken_for_employer():
    text="""陈欢
2024届贵州定向选调生
文学院2020级汉语言文学专业本科生
贵州省石阡县县委办公室
试用期公务员（不定职级）"""
    row=extract_experience_records(text,"贵州定向选调经验分享")[0]
    assert row["city"]=="贵州省石阡县"
    assert row["employer"]=="贵州省石阡县县委办公室"


def test_wrapped_employer_and_position_are_rejoined():
    text="""张翠英
2024届福建选调生
民族学与社会学学院2021级社会学专业硕士研究生
入职福建省三明市宁化县委社会工
作部，现任职翠江镇中山村党支部
书记助理"""
    row=extract_experience_records(text,"福建选调经验分享")[0]
    assert row["city"]=="福建省三明市"
    assert row["employer"]=="福建省三明市宁化县委社会工作部"
    assert row["position"]=="翠江镇中山村党支部书记助理"


def test_shared_poster_belongs_to_matching_article_only():
    poster="许文博\n2024届河北定向选调生\n保定市徐水区财政局"
    assert shared_image_relevant("闪耀基层——河北定向选调经验分享",poster)
    assert not shared_image_relevant("闪耀基层——山西定向选调经验分享",poster)


def test_selection_year_is_not_invented_as_graduation_year():
    text="""李林海
2024年四川省紧缺（定向）选调生
理学院2020级纳米材料与技术专业本科生
四川省德阳市中江县市场监督管理局
试用期公务员（不定职级）
李云祥
2024年四川紧缺（定向）选调生
民族学与社会学学院2021级马克思主义民族理论与政策专业硕士生
四川省凉山州宁南县纪委监委
试用期公务员（不定职级）"""
    rows=extract_experience_records(text,"四川定向选调经验分享")
    assert [r["student_name"] for r in rows]==["李林海","李云祥"]
    assert all(r["graduation_year"]=="待人工核对" and r["needs_review"] for r in rows)
    assert rows[0]["employer"]=="四川省德阳市中江县市场监督管理局"
