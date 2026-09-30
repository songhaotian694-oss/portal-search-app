export type Facet = 'year' | 'dateYear' | 'major' | 'city' | 'type' | 'degree' | 'position'

export interface QueryToken {
  facet: Facet
  label: string
  value: string
}

export interface ExperienceRecord {
  id: string
  person: string
  year: number
  major: string
  degree: string
  city: string
  province: string
  position: string
  organization: string
  type: string
  title: string
  excerpt: string
  detail: string
  source: string
  date: string
  keywords: string[]
  sourceUrl?: string
  needsReview?: boolean
  missingFields?: string[]
}

export interface SearchFilters {
  year?: string
  dateYear?: string
  major?: string
  city?: string
  degree?: string
  type?: string
  position?: string
}

export interface SearchResponse {
  records: ExperienceRecord[]
  total: number
  elapsedMs: number
  analysis: AnalyticsSummary
}

export interface AnalyticsSummary {
  total: number
  needsReview: number
  cities: [string, number][]
  positions: [string, number][]
  majors: [string, number][]
  years: [string, number][]
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary
  relations: {
    nodes: { dimension: string; value: string; count: number }[]
    links: { fromDimension: string; fromValue: string; toDimension: string; toValue: string; count: number }[]
  }
  dimensions: string[]
}

export interface Overview {
  records: number
  cities: number
  majors: number
  latestYear: number
  articles: number
  needsReview: number
  lastSync: string | null
}
