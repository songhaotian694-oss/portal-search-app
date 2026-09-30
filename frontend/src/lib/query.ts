import rules from '../../../config/search_rules.json'
import type { Facet, QueryToken } from '../types'

export const facetNames: Record<Facet, string> = {
  year: '届别', dateYear: '发布年份', major: '专业', city: '地区', type: '类型', degree: '学历', position: '岗位',
}

const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const negativePattern = /排除|不要|不含|不包括|不看|不是|不在|除了|非/
const candidates = new Map<string, { facet: Facet; value: string }>()
for (const facet of ['city', 'major', 'degree', 'position'] as const) {
  for (const [value, aliases] of Object.entries(rules[facet])) {
    for (const alias of aliases) candidates.set(alias.toLocaleLowerCase(), { facet, value })
  }
}
const aliases = [...candidates.keys()].sort((a, b) => b.length - a.length)
const entity = aliases.map(alias => /^[a-z]+$/i.test(alias) ? `(?<![a-z])${escape(alias)}(?![a-z])` : escape(alias)).join('|')
const pattern = new RegExp(`20\\d{2}\\s*(?:届)?\\s*(?:至|到|[-~—–])\\s*20\\d{2}\\s*届|20\\d{2}\\s*(?:届|级|年(?:毕业|毕业生|发布|收录)?)|${entity}`, 'gi')

export function parseQuery(query: string): QueryToken[] {
  const text = query.normalize('NFKC')
  const tokens: QueryToken[] = []
  let previousEnd = 0
  let previousFacet = ''
  let negative = false
  // Preview chips are descriptive; the backend receives the complete query.
  // Quoted phrases and labeled fields are not inferred again here.
  const masked = text.replace(/(?:排除|不要|不含)?["“][^"”]+["”]|(?:姓名|单位|岗位|专业|地区|学历)\s*[:：]\s*[^\s，,；;。]+/g, match => ' '.repeat(match.length))
  for (const match of masked.matchAll(pattern)) {
    const raw = match[0]
    const gap = masked.slice(previousEnd, match.index)
    let facet: Facet
    let value: string
    if (/^20\d{2}/.test(raw)) {
      if (raw.includes('级')) { previousEnd = match.index + raw.length; previousFacet = ''; continue }
      facet = raw.includes('年') && !raw.includes('毕业') ? 'dateYear' : 'year'
      const years = raw.match(/20\d{2}/g)!
      value = years.length === 2 ? years.join('–') : years[0]
    } else ({ facet, value } = candidates.get(raw.toLocaleLowerCase())!)
    if (negativePattern.test(gap)) negative = true
    else if (facet !== previousFacet || /[,，;；。]|但是|而是|只要/.test(gap)) negative = false
    const shown = negative ? `排除${value}` : value
    const token = tokens.find(item => item.facet === facet)
    if (token) {
      if (!token.value.split(' / ').includes(shown)) token.value += ` / ${shown}`
      token.sources!.push(raw)
    } else tokens.push({ facet, label: facetNames[facet], value: shown, sources: [raw] })
    previousEnd = match.index + raw.length
    previousFacet = facet
  }
  return tokens
}
