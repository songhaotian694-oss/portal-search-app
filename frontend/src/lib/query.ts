import type { Facet, QueryToken, SearchFilters } from '../types'

export const facetNames: Record<Facet, string> = {
  year: '届别', dateYear: '年份', major: '专业', city: '地区', type: '类型', degree: '学历', position: '岗位',
}

const majors = ['计算机科学与技术', '计算机', '软件工程', '电子信息', '公共管理', '新闻传播', '汉语言文学', '统计学', '社会学', '经济学', '法学']
const cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '南京', '武汉', '重庆', '苏州', '西安']
const positions = ['数字治理', '数据分析', '信息技术', '基层治理', '政策研究', '组织人事', '宣传策划', '文字综合', '法制审核', '经济发展', '社会工作', '综合管理']

export function parseQuery(query: string): QueryToken[] {
  const tokens: QueryToken[] = []
  const add = (facet: Facet, value: string) => {
    if (!tokens.some(token => token.facet === facet)) tokens.push({ facet, label: facetNames[facet], value })
  }
  const year = query.match(/20\d{2}\s*届/)
  if (year) add('year', year[0].match(/20\d{2}/)![0])
  const dateYear = query.match(/20\d{2}\s*年/)
  if (dateYear) add('dateYear', dateYear[0].match(/20\d{2}/)![0])
  const major = majors.find(item => query.includes(item))
  if (major) add('major', major)
  const city = cities.find(item => query.includes(item))
  if (city) add('city', city)
  if (/选调|公务员/.test(query)) add('type', '选调经验')
  if (/博士|硕士|本科/.test(query)) add('degree', query.match(/博士|硕士|本科/)![0])
  const position = positions.find(item => query.includes(item))
  if (position) add('position', position)
  return tokens
}

export function tokensToFilters(tokens: QueryToken[]): SearchFilters {
  return Object.fromEntries(tokens.map(token => [token.facet, token.value])) as SearchFilters
}

export function freeText(query: string, tokens: QueryToken[]): string {
  let text = query
  for (const token of tokens) text = text.replaceAll(token.value, '')
  return text.replace(/查找|搜索|检索|寻找|关于|相关|收录|的|在|和|与|专业|地区|城市|岗位|经验|信息|届|年|选调|公务员|[\s，,。]+/g, '').trim()
}
