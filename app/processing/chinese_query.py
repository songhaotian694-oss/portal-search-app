"""Small, offline query planner shared by search and filtered export.

Structured fields remain the evidence boundary: matching a city in the source
article title must not assign that city to every person in the article.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from ..settings import RESOURCE_ROOT

NEGATIVE = r'排除|不要|不含|不包括|不看|不是|不在|除了|非'
FIELDS = ('student_name', 'graduation_year', 'grade', 'degree', 'major', 'city', 'employer', 'position')


@lru_cache(maxsize=1)
def rules() -> dict:
    return json.loads((RESOURCE_ROOT / 'config' / 'search_rules.json').read_text(encoding='utf-8'))


def variants(field_name: str, value: str) -> list[str]:
    for canonical, aliases in rules().get(field_name, {}).items():
        if value.casefold() in [x.casefold() for x in aliases]:
            return rules()['match_values'].get(canonical, [canonical])
    return [value]


@dataclass
class QueryPlan:
    include: dict[str, list[str]] = field(default_factory=dict)
    exclude: dict[str, list[str]] = field(default_factory=dict)
    terms: list[list[str]] = field(default_factory=list)
    excluded_terms: list[str] = field(default_factory=list)
    date_from: str = ''
    date_to: str = ''

    def add(self, key: str, values: list[str], negative: bool = False) -> None:
        target = self.exclude if negative else self.include
        target[key] = list(dict.fromkeys([*target.get(key, []), *values]))


def parse_query(query: str, vocabulary: dict[str, list[str]] | None = None) -> QueryPlan:
    plan = QueryPlan()
    text = unicodedata.normalize('NFKC', query).strip()
    # Quoted phrases and explicit field labels take precedence over inference.
    def quoted(match):
        value = match.group(2)
        if match.group(1): plan.excluded_terms.append(value)
        else: plan.terms.append([value])
        return ' ' * len(match.group())
    text = re.sub(r'(?:(' + NEGATIVE + r')\s*)?["“]([^"”]+)["”]', quoted, text)
    labels = {'姓名': 'student_name', '单位': 'employer', '岗位': 'position', '专业': 'major', '地区': 'city', '学历': 'degree'}
    def labeled(match):
        key = labels[match.group(2)]
        values = [v for part in re.split(r'或|或者|/|、', match.group(3)) for v in variants(key, part)]
        plan.add(key, values, bool(match.group(1)))
        return ' ' * len(match.group())
    text = re.sub(r'(?:(' + NEGATIVE + r')\s*)?(姓名|单位|岗位|专业|地区|学历)\s*[:：]\s*([^\s，,；;。]+)', labeled, text)

    candidates = {}
    for key in ('student_name', 'employer', 'city', 'major', 'degree', 'position'):
        for canonical, aliases in rules().get(key, {}).items():
            for alias in aliases: candidates[alias.casefold()] = (key, variants(key, canonical))
        for value in (vocabulary or {}).get(key, []):
            if value and value not in {'待人工核对', '待核对', '未提取'}:
                candidates.setdefault(value.casefold(), (key, variants(key, value)))
    # Regions outside the public list can be learned from local structured data.
    for value in (vocabulary or {}).get('city', []):
        short = re.sub(r'(?:市|省|自治区)?(?:[（(].*?[）)])?$', '', value)
        if len(short) >= 2: candidates.setdefault(short.casefold(), ('city', [short]))
    aliases = sorted(candidates, key=len, reverse=True)
    entity = '|'.join(re.escape(x) if not x.isascii() else r'(?<![A-Za-z])' + re.escape(x) + r'(?![A-Za-z])' for x in aliases)
    year = r'20\d{2}\s*(?:届)?\s*(?:至|到|[-~—–])\s*20\d{2}\s*届|20\d{2}\s*(?:届|级|年(?:毕业|毕业生|发布|收录)?)'
    pattern = re.compile(year + '|' + entity, re.I)
    previous_end = 0; previous_key = ''; negative = False
    spans = []
    for match in pattern.finditer(text):
        raw = match.group(); gap = text[previous_end:match.start()]
        if re.match(r'20\d{2}', raw):
            years = re.findall(r'20\d{2}', raw)
            if '级' in raw: key = 'grade'; values = years
            elif '年' in raw and '毕业' not in raw:
                key = 'date'; values = years
            else:
                key = 'graduation_year'
                values = [str(y) for y in range(int(years[0]), int(years[-1]) + 1)] if len(years) > 1 else years
                if not values: values = ['invalid-year-range']
        else: key, values = candidates[raw.casefold()]
        negation = re.search(NEGATIVE, gap)
        if negation: negative = True
        elif key != previous_key or re.search(r'[,，;；。]|但是|而是|只要', gap): negative = False
        if key == 'date':
            # Publication year stays distinct from graduation year.
            if not negative:
                plan.date_from = f'{values[0]}-01-01'; plan.date_to = f'{values[-1]}-12-31'
            else: plan.add('published_at', values, True)
        else: plan.add(key, values, negative)
        spans.append((previous_end + negation.start() if negation else match.start(), match.end()))
        previous_end = match.end(); previous_key = key
    for start, end in reversed(spans): text = text[:start] + ' ' * (end-start) + text[end:]
    # Do not delete single characters globally: they can belong to a name or unit.
    text = re.sub(r'找一下|查一下|帮我|请问|请帮忙|有没有|查找|查询|搜索|检索|寻找|看看|哪些|相关|选调生?|经验分享|毕业生|毕业|同学', ' ', text)
    for part in re.split(r'[\s，,。；;]+', text):
        part = re.sub(r'^(?:的|在|和|与|或|或者|以及|从|到|有|是|了|生|年|届|市|省)+|(?:的人|的|生|市|省|吗|呢|有)$', '', part)
        part = re.sub(r'(?:工作|就业|入职)$', '', part)
        if not part: continue
        negative_match = re.match(r'^(?:' + NEGATIVE + r')(.+)$', part)
        if negative_match: plan.excluded_terms.append(negative_match.group(1))
        elif re.fullmatch(NEGATIVE + r'|或者|或|和|与|以及|在|的|到|人|生|只要|但|不|不要|专业|地区|城市|学历|岗位|信息|工作|就业|入职|名单', part): continue
        else:
            choices = [x for x in re.split(r'或者|或|/|、', part) if x]
            if choices: plan.terms.append(choices)
    return plan
