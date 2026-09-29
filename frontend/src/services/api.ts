import { mockRecords } from '../data/mock'
import { freeText, parseQuery, tokensToFilters } from '../lib/query'
import type { ExperienceRecord, Facet, Overview, SearchFilters, SearchResponse } from '../types'

const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

/** Mock boundary: replace these methods with HTTP calls when the Python API is connected. */
export const api = {
  async getOverview(): Promise<Overview> {
    await wait(180)
    return {
      records: mockRecords.length,
      cities: new Set(mockRecords.map(record => record.city)).size,
      majors: new Set(mockRecords.map(record => record.major)).size,
      latestYear: Math.max(...mockRecords.map(record => record.year)),
    }
  },
  async getRecords(): Promise<ExperienceRecord[]> {
    await wait(140)
    return mockRecords
  },
  async searchRecords(query: string, filters?: SearchFilters, priority: Facet[] = []): Promise<SearchResponse> {
    const started = performance.now()
    await wait(220)
    const parsed = parseQuery(query)
    const merged = filters ?? tokensToFilters(parsed)
    const remaining = freeText(query, parsed).toLowerCase()
    const records = mockRecords.filter(record => {
      if (merged.year && String(record.year) !== merged.year) return false
      if (merged.dateYear && !record.date.startsWith(merged.dateYear)) return false
      if (merged.major && !record.major.includes(merged.major)) return false
      if (merged.city && !`${record.city}${record.province}`.includes(merged.city)) return false
      if (merged.degree && record.degree !== merged.degree) return false
      if (merged.type && record.type !== merged.type) return false
      if (merged.position && !record.position.includes(merged.position)) return false
      if (remaining && !`${record.title}${record.excerpt}${record.organization}${record.person}`.toLowerCase().includes(remaining)) return false
      return true
    })
    const order = priority.length ? priority : parsed.map(token => token.facet)
    const score = (record: ExperienceRecord) => order.reduce((total, facet, index) => {
      const value = merged[facet]
      if (!value) return total
      const field = facet === 'year' ? String(record.year) : facet === 'dateYear' ? record.date.slice(0, 4) : record[facet]
      const strength = field === value ? 2 : field.includes(value) ? 1 : 0
      const evidence = record.excerpt.includes(value) ? 1 : 0
      return total + (order.length - index) * (strength + evidence) * 3
    }, record.confidence)
    records.sort((a, b) => score(b) - score(a) || b.confidence - a.confidence)
    return { records, total: records.length, elapsedMs: Math.max(240, Math.round(performance.now() - started)) }
  },
}
