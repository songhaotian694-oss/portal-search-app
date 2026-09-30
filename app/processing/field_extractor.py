from __future__ import annotations
import re
from pathlib import Path
from ..settings import CONFIG_DIR

def words(file: str) -> list[str]:
    p=CONFIG_DIR/file
    return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")] if p.exists() else []
def sentences(text: str) -> list[str]: return [x.strip() for x in re.split(r"(?<=[。！？；\n])",text) if x.strip()]
def first_pattern(text: str, patterns: list[str]) -> str | None:
    for p in patterns:
        m=re.search(p,text)
        if m:return m.group(0)
    return None
def locate(text: str, value: str | None) -> str:
    if not value:return ""
    return next((s for s in sentences(text) if value in s), "")
def extract_fields(text: str, source: str="正文") -> dict:
    graduation=first_pattern(text,[r"20\d{2}届"]); grade=first_pattern(text,[r"20\d{2}级"])
    degree=first_pattern(text,[r"博士(?:研究生|毕业生)?",r"硕士(?:研究生|毕业生)?",r"本科(?:生|毕业生)?"])
    major=next((x for x in words("majors.txt") if x in text),None); city=next((x for x in words("cities.txt") if x in text),None)
    hints=[s for s in sentences(text) if any(k in s for k in ["选调","录用","入职","任职","单位","岗位","报到","组织部","街道","乡镇","机关"])]
    evidence=hints[0] if hints else ""
    employer=None; position=None
    if evidence:
        m=re.search(r"(?:录用至|入职|就职于|任职于|报到|单位为)[：:、 ]*([^，。；;（）()]{2,40})",evidence)
        employer=m.group(1).strip() if m else None
        p=re.search(r"(?:岗位|职位|任职为|担任)[：:、 ]*([^，。；;（）()]{2,30})",evidence)
        position=p.group(1).strip() if p else None
    vals={"graduation_year":graduation,"grade":grade,"degree":degree,"major":major,"city":city,"employer":employer,"position":position}
    evidence_map={k:{"source":source,"sentence": locate(text,v) if v else evidence} for k,v in vals.items()}
    for k,v in vals.items(): vals[k]=v or "待人工核对"
    vals["evidence"]=evidence_map; vals["needs_review"]=any(v=="待人工核对" for v in vals.values() if isinstance(v,str))
    return vals

def is_experience_share(title:str)->bool:
    return "选调" in title and "经验分享" in title

def shared_image_relevant(title:str,text:str)->bool:
    """相同海报挂在多个通知下时，只保留与海报选调地区一致的通知。"""
    match=re.search(r"[—–-]+([^—|]{2,20}?)(?:定向|常规|普通|专项|集中)?选调",title)
    if not match:return False
    region=match.group(1)
    return any(region in line and "选调生" in line for line in text.splitlines())

PROVINCES=("内蒙古自治区","广西壮族自治区","西藏自治区","宁夏回族自治区","新疆维吾尔自治区",
           "黑龙江省","吉林省","辽宁省","河北省","山西省","陕西省","山东省","河南省",
           "江苏省","浙江省","安徽省","福建省","江西省","湖北省","湖南省","广东省",
           "海南省","四川省","贵州省","云南省","甘肃省","青海省","台湾省",
           "北京市","天津市","上海市","重庆市","香港特别行政区","澳门特别行政区")

def employment_region(employer:str,title:str)->str|None:
    """只从单位原文提取明确出现的行政区域，不把“市场”“市镇”当作市名。"""
    place=re.sub(r"^(?:入职|就职于|任职于|中共)","",employer)
    province=next((name for name in PROVINCES if place.startswith(name)),"")
    rest=place[len(province):]
    if province.endswith("市"):
        return province
    city=re.match(r"([^县]{2,8}?市)(?!镇)",rest)
    if city:
        # 直辖市以外，原文可能同时写地级市和县级市。
        following=rest[city.end():]
        nested=re.match(r"([^县]{2,8}?市)(?!镇)",following)
        return province+city.group(1)+(nested.group(1) if nested else "")
    prefecture=re.match(r"(.{2,10}?(?:地区|州|盟))",rest)
    if prefecture:return province+prefecture.group(1)
    county=re.match(r"(.{2,12}?(?:自治县|县))",rest)
    if county:return province+county.group(1)
    district=re.match(r'(.{2,10}?区)',rest)
    if district:return province+district.group(1)
    if province:return province+"（省级单位）"
    title_region=re.search(r"——([^—|]{2,12}?)(?:定向|普通|专项|集中)?选调",title)
    return title_region.group(1)+"（地区）" if title_region else None

PIPELINE_VERSION = 'auto-20260930-1'
MISSING = '待人工核对'  # Existing database/API compatibility; UI describes absent fields.
RECORD_FIELDS = ('student_name','graduation_year','grade','degree','major','city','employer','position')
DEGREE_PATTERN = r'第二学士学位(?:毕业生)?|博士(?:研究生|毕业生|生)?|硕士(?:研究生|毕业生|生)?|本科(?:毕业生|生)?|研究生'
JOB_PATTERN = r'试用期公务员|公务员|(?:一级|二级|三级|四级)?(?:主任)?科员|党(?:总支|支部)书记助理|书记助理|主任助理|干部'


def missing_fields(record:dict)->list[str]:
    return [key for key in RECORD_FIELDS if not record.get(key) or record[key] in {MISSING,'待核对'}]


def validate_ocr_record(record:dict,ocr_lines:list[dict])->dict:
    """Withhold a field supported only by low confidence text after bounded retries."""
    text='';ranges=[]
    for line in ocr_lines:
        start=len(text);text+=re.sub(r'\s+','',line['text'])
        ranges.append((start,len(text),line['score']))
    confidence={};withheld=[]
    for key in RECORD_FIELDS:
        value=record[key]
        if value==MISSING:continue
        needle=re.sub(r'（省级单位）|\s+','',value)
        scores=[]
        for match in re.finditer(re.escape(needle),text):
            scores.append(min(score for start,end,score in ranges if start<match.end() and end>match.start()))
        if scores:
            confidence[key]=round(max(scores),4)
            if max(scores)<.80:record[key]=MISSING;withheld.append(key)
    absent=missing_fields(record)
    record['needs_review']=bool(absent)
    record['quality'].update(missing_fields=absent,status='partial' if absent else 'complete',confidence=confidence,withheld_fields=withheld)
    return record


def _name_before(lines:list[str],index:int)->str|None:
    # Names belong to the nearest status line, never to headings further away.
    for candidate in reversed(lines[max(0,index-6):index]):
        if re.search(r'20\d{2}届|20\d{2}年.*选调|分享|活动|选调|扫码|腾讯|秋招|同行|就业|沙龙|校友介绍',candidate):
            break
        if re.search(r'20\d{2}级|学院|专业|本科|硕士|博士|研究生|级本科',candidate):continue
        if re.fullmatch(r'[\u4e00-\u9fff·]{2,8}',candidate) and not re.search(r'公务员|助理|研究生|本科生|职级|政府|局|工会|办公室|委员会',candidate):
            return candidate
    return None


def _record_from_block(lines:list[str],name:str|None)->dict:
    compact=''.join(lines).replace('硕土','硕士')
    graduation=first_pattern(lines[0],[r'20\d{2}届'])
    grades=list(dict.fromkeys(re.findall(r'20\d{2}级',compact)))
    education=[]
    for i,line in enumerate(lines):
        if re.search(r'20\d{2}级|学院',line):
            education.append(line)
            for tail in lines[i+1:i+3]:
                if re.search(r'20\d{2}|省|市|县|局|政府|公务员|科员|书记',tail):break
                if re.search(r'专业|本科|硕士|博士|学士|研究生',tail) or len(tail)<=8:education.append(tail)
    academic=''.join(education).replace('硕土','硕士')
    degree=first_pattern(academic or compact,[DEGREE_PATTERN])
    if '研究生' in academic and '本科生' in academic and '硕士' not in academic:degree='研究生、本科生'
    major=None
    if grades:
        match=re.search(re.escape(grades[0])+r'(.{2,65}?)(?:专业|第二学士学位|本科(?:生|毕业生)|硕士(?:生|研究生)|博士(?:生|研究生)|研究生)',academic)
        if match:major=match.group(1).rsplit('学院',1)[-1]
    if not major:
        named_major=re.match(r'(.{2,65}?)专业',academic.rsplit('学院',1)[-1])
        if named_major:major=named_major.group(1)
    if not major:major=next((item for item in sorted(words('majors.txt'),key=len,reverse=True) if item in academic.rsplit('学院',1)[-1]),None)
    employment=[]
    for line in lines[1:]:
        if re.search(r'扫码|腾讯|招生就业|关注我们|参加|职”等|^MUC|\d{1,2}月\d{1,2}日',line):break
        if line in education or re.search(r'20\d{2}级|20\d{2}届|20\d{2}年.*选调生',line):continue
        if line in {'米','来','木'} or line==name:continue
        employment.append(line)
    # A selected person's status may itself contain the explicit employer.
    status=re.search(r'20\d{2}年(.+?)选调生',lines[0])
    if status and re.search(r'局|委|办|部|厅|院|政府',status.group(1)):employment.insert(0,status.group(1))
    organization=r'局|委|办|部|厅|院|政府|街道|乡|镇|村|社区|公司|学校|医院|联社|档案馆|工会|残联|地区|州|盟|县'
    start=next((i for i,line in enumerate(employment) if re.search(organization,line) and not re.fullmatch(JOB_PATTERN+r'.*',line)),None)
    employer=None;position=None
    if start is not None:
        if start and re.fullmatch(r'.{2,20}(?:省|自治区|市|州|县)',employment[start-1]):start-=1
        joined=''.join(employment[start:])
        joined=re.sub(r'^(?:现)?(?:入职|就职于|任职于)','',joined)
        if '现任职' in joined:
            employer,position=joined.split('现任职',1)
        else:
            job=re.search(r'综合职位|(?:岗位(?:为)?|职位(?:为)?)[：:]?|'+JOB_PATTERN,joined)
            if job:
                employer=joined[:job.start()]
                position=joined[job.start():]
                position=re.sub(r'^(?:岗位(?:为)?|职位(?:为)?)[：:]?','',position)
            else:employer=joined
        employer=(employer or '').strip('，,；;：: ') or None
    if not position:
        position=next((line for line in employment if re.search(JOB_PATTERN,line)),None)
    city=employment_region(employer,'') if employer else None
    if not city:
        region_line=next((line for line in employment if re.fullmatch(r'.{2,30}(?:省|自治区|市|区|县)',line)),None)
        if region_line:city=employment_region(region_line,'')
    values=dict(student_name=name,graduation_year=graduation,grade='、'.join(grades) or None,degree=degree,major=major,city=city,employer=employer,position=position)
    values={key:value or MISSING for key,value in values.items()}
    absent=missing_fields(values)
    values.update(evidence_text='\n'.join(([name] if name else [])+lines),needs_review=bool(absent),quality={'version':PIPELINE_VERSION,'missing_fields':absent,'status':'partial' if absent else 'complete'})
    return values


def extract_experience_records(text:str,title:str='')->list[dict]:
    """Anchor people to explicit graduation/selection status, then join wrapped fields."""
    if not is_experience_share(title):return []
    lines=[re.sub(r'[ \t]+','',line.strip()) for line in text.splitlines() if line.strip()]
    # Selection status may wrap after the year/employer; restore that anchor first.
    for i in range(len(lines)-2,-1,-1):
        if re.search(r'20\d{2}年',lines[i]) and '选调生' not in lines[i] and '选调生' in lines[i+1]:
            lines[i]+=lines.pop(i+1)
    anchors=[i for i,line in enumerate(lines) if re.search(r'20\d{2}届|20\d{2}年.{0,40}选调生',line)]
    records=[]
    for n,start in enumerate(anchors):
        end=anchors[n+1] if n+1<len(anchors) else len(lines)
        next_name=_name_before(lines,end) if n+1<len(anchors) else None
        name=_name_before(lines,start)
        name_index=next((i for i in range(start-1,max(-1,start-7),-1) if lines[i]==name),start)
        block=[lines[start],*lines[name_index+1:start],*lines[start+1:end]]
        if next_name and next_name in block:block=block[:block.index(next_name)]
        record=_record_from_block(block,name)
        # Keep an unnamed but substantive block; suppress empty/header-only guesses.
        substantive=sum(record[key]!=MISSING for key in ('degree','major','employer','position'))
        if substantive>=2 or (name and (substantive>=1 or record['city']!=MISSING)):records.append(record)
    return records


def extract_without_graduation_year(text:str,title:str)->list[dict]:
    return extract_experience_records(text,title)
