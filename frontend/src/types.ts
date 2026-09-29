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
  confidence: number
  keywords: string[]
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
}

export interface Overview {
  records: number
  cities: number
  majors: number
  latestYear: number
}
