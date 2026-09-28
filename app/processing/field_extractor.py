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
    if province:return province+"（省级单位）"
    title_region=re.search(r"——([^—|]{2,12}?)(?:定向|普通|专项|集中)?选调",title)
    return title_region.group(1)+"（地区）" if title_region else None

def extract_without_graduation_year(text:str,title:str)->list[dict]:
    """兼容只写选调年份的海报；选调年份不能当作毕业届别。"""
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    names=[]
    for i,line in enumerate(lines):
        if not re.fullmatch(r"[\u4e00-\u9fff·]{2,15}",line) or any(
                word in line for word in ["分享","活动","选调","沙龙","就业","学院","公务员","助理","研究生","本科生","介绍","考试","考情","建议"]):
            continue
        nearby="".join(lines[i+1:i+5])
        if re.search(r"20\d{2}级",nearby) and re.search(r"20\d{2}年.{0,35}选调生","".join(lines[i+1:i+7])):
            names.append(i)
    records=[]
    for n,start in enumerate(names):
        block=lines[start:names[n+1] if n+1<len(names) else min(len(lines),start+12)]
        compact="".join(block).replace("硕土","硕士")
        grades=list(dict.fromkeys(re.findall(r"20\d{2}级",compact)))
        grade="、".join(grades) if grades else None
        degree=first_pattern(compact,[r"博士(?:研究生|毕业生)?",r"硕士(?:研究生|毕业生|生)?",r"本科(?:生|毕业生)?",r"研究生"])
        if "研究生" in compact and "本科生" in compact and "硕士" not in compact:
            degree="研究生、本科生"
        major=None
        if grades:
            major_match=re.search(re.escape(grades[0])+r"(.{2,55}?)专业",compact)
            if major_match:major=major_match.group(1).rsplit("学院",1)[-1]
        position=next((line for line in block if "试用期公务员" in line or "科员" in line),None)
        employer=None
        for j,line in enumerate(block[1:],1):
            if re.match(r"20\d{2}年",line):
                status_text=line
                if "选调生" not in status_text:
                    status_text+="".join(block[j+1:j+3])
                status=re.match(r"20\d{2}年(.+?)选调生",status_text)
                if status and any(word in status.group(1) for word in ["局","委","办","部","厅","院","政府","纪委","监委"]):
                    employer=status.group(1)
            elif "选调生" in line:
                continue
            elif any(word in line for word in ["局","委","办","部","厅","院","政府","纪委","监委"]):
                if "学院" not in line:employer=line
            if employer:break
        city=employment_region(employer,title) if employer else None
        values={"student_name":block[0],"graduation_year":None,"grade":grade,"degree":degree,
                "major":major,"city":city,"employer":employer,"position":position}
        values={key:(value or "待人工核对") for key,value in values.items()}
        values.update(evidence_text="\n".join(block[:12]),needs_review=True)
        records.append(values)
    return records

def extract_experience_records(text:str,title:str="")->list[dict]:
    """把一张或多张海报中的多名分享者拆成独立就业记录。"""
    if not is_experience_share(title):return []
    normalized=re.sub(r"[ \t]+","",text)
    lines=[line.strip() for line in normalized.splitlines() if line.strip()]
    graduation_line_indexes=[i for i,line in enumerate(lines) if re.search(r"20\d{2}届",line)]
    starts=list(re.finditer(r"20\d{2}届",normalized))
    if not starts:return extract_without_graduation_year(text,title)
    records=[]
    for index,match in enumerate(starts):
        end=starts[index+1].start() if index+1<len(starts) else min(len(normalized),match.start()+500)
        block=normalized[match.start():end]
        compact=re.sub(r"\s+","",block)
        compact=compact.replace("硕土","硕士")
        block_lines=[line for line in block.splitlines() if line]
        graduation=match.group(0)
        student_name=None
        if index<len(graduation_line_indexes) and graduation_line_indexes[index]:
            year_line=graduation_line_indexes[index]
            # OCR偶尔会在人名和届别之间插入单个噪声字，向前检查最多4行。
            for distance in range(1,min(5,year_line+1)):
                candidate=lines[year_line-distance]
                if re.fullmatch(r"[\u4e00-\u9fff·]{2,15}",candidate) and not any(word in candidate for word in ["分享","活动","选调","沙龙","就业","学院","公务员","助理","研究生","本科生"]):
                    student_name=candidate;break
        grade=first_pattern(compact,[r"20\d{2}级"])
        degree=first_pattern(compact,[r"博士(?:研究生|毕业生)?",r"硕士(?:研究生|毕业生)?",r"本科(?:生|毕业生)?",r"研究生"])
        major=None
        if grade:
            major_match=re.search(re.escape(grade)+r"(.{2,55}?)专业",compact)
            if major_match:
                major=major_match.group(1)
                if "学院" in major:major=major.rsplit("学院",1)[-1]
            else:
                # 部分海报写“实验班本科生”而没有“专业”二字。
                major_match=re.search(re.escape(grade)+r"(.{2,55}?)(?:本科生|硕士生|硕士研究生|研究生)",compact)
                if major_match:
                    major=major_match.group(1)
                    if "学院" in major:major=major.rsplit("学院",1)[-1]
        if not major:
            major=next((item for item in words("majors.txt") if item in compact),None)
        position_line=next((line for line in block_lines if any(k in line for k in ["书记助理","主任助理","岗位","职位","科员","干部","公务员"])),"")
        organization_words=["局","委","办","部","厅","院","政府","街道","乡","镇","村","社区","公司","学校","医院","联社","档案馆","地区","州","盟","县"]
        place_index=next((i for i,line in enumerate(block_lines) if line!=position_line and any(k in line for k in organization_words)
                          and not any(k in line for k in ["学院","专业","研究生","本科生","选调生"])
                          and not re.search(r"20\d{2}届",line)),None)
        place_line=block_lines[place_index] if place_index is not None else ""
        # 单位名称偶尔被OCR拆成两行，把紧邻且含行政区名称的上一行合并回来。
        if (place_index and re.search(r"(?:省|自治区|市|地区|州|县)",block_lines[place_index-1])
                and not re.search(r"20\d{2}届|选调生",block_lines[place_index-1])):
            place_line=block_lines[place_index-1]+place_line
        # “社会工 / 作部，现任职……”这类换行要接回单位，并取出真实岗位。
        if place_index is not None and place_index+1<len(block_lines) and "现任职" in block_lines[place_index+1]:
            place_line+=block_lines[place_index+1]
        if "现任职" in place_line:
            place_line,position_from_employer=place_line.split("现任职",1)
            place_line=place_line.rstrip("，,；; ")
            if position_from_employer:
                if position_line and position_line not in position_from_employer:
                    position_from_employer+=position_line
                position_line=position_from_employer
        place_line=re.sub(r"^(?:入职|就职于|任职于)","",place_line)
        city=employment_region(place_line,title) if place_line else None
        position=position_line or None
        employer=place_line or ((city+"（具体单位未注明）") if city else None)
        evidence="\n".join(block.splitlines()[:12])
        values={"student_name":student_name,"graduation_year":graduation,"grade":grade,"degree":degree,"major":major,"city":city,"employer":employer,"position":position}
        values={key:(value or "待人工核对") for key,value in values.items()}
        values.update(evidence_text=evidence,needs_review=any(value=="待人工核对" for value in values.values()))
        records.append(values)
    return records
