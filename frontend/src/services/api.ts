import type { AnalyticsResponse, AnalyticsSummary, ExperienceRecord, Facet, Overview, SearchFilters, SearchResponse } from '../types'

type RawRecord = {
  id: number; article_id: number; record_no: number; student_name: string; graduation_year: string
  grade: string; degree: string; major: string; city: string; employer: string; position: string
  evidence_text: string; needs_review: number; title: string; published_at: string
  detail_url: string; collected_at: string; quality_json?: string
}

export type JobStatus = { status: string; current: number; total: number; success?: number; failed?: number; message: string; resume_available?: boolean }
export type AuthStatus = { started?: boolean; logged_in: boolean; url: string; remember_login: boolean; embedded: boolean; login_open: boolean; message?: string }
export type PortalSettings = { portal_url: string; employment_entry: string; allowed_domains: string[]; data_source: string; api_keywords: string[] }

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options?.headers } }) }
  catch { throw new Error('无法连接本地服务，请通过软件 EXE 启动。') }
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string }
    throw new Error(typeof body.detail === 'string' ? body.detail : `请求失败（${response.status}）`)
  }
  return response.json() as Promise<T>
}

function normalize(value?: string | null): string { return value && value !== '待人工核对' ? value : '' }
function toRecord(raw: RawRecord): ExperienceRecord {
  const year = Number(normalize(raw.graduation_year).match(/20\d{2}/)?.[0] || 0)
  const date = raw.published_at || raw.collected_at || ''
  const evidence = raw.evidence_text || ''
  const fields: Record<string, string> = { graduation_year: '届别', grade: '入学年级', degree: '学历', major: '专业', city: '地区', employer: '单位', position: '岗位' }
  const missing = Object.entries(fields).filter(([key]) => !normalize(raw[key as keyof RawRecord] as string)).map(([, label]) => label)
  return {
    id: String(raw.id), person: normalize(raw.student_name) || `记录 ${raw.id}`, year,
    major: normalize(raw.major) || '未提取', degree: normalize(raw.degree) || '未提取',
    city: normalize(raw.city) || '未提取', province: normalize(raw.city) || '',
    position: normalize(raw.position) || '未提取', organization: normalize(raw.employer) || '未提取',
    type: '选调经验', title: raw.title || '选调经验分享',
    excerpt: evidence.slice(0, 150) || '暂无证据文字，请查看来源文章并核对提取结果。',
    detail: evidence || '暂无 OCR 证据文字。', source: raw.title || '本地文章', date,
    keywords: [raw.graduation_year, raw.major, raw.city, raw.position].filter(Boolean),
    sourceUrl: raw.detail_url, needsReview: Boolean(raw.needs_review), missingFields: missing,
  }
}

const json = (data: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(data) })

function searchParameters(query: string, filters?: SearchFilters): URLSearchParams {
  const merged = filters ?? {}
  const params = new URLSearchParams()
  if (query.trim()) params.set('q', query.trim())
  if (merged.year) params.set('graduation_year', merged.year)
  for (const key of ['degree', 'major', 'city', 'position'] as const) if (merged[key]) params.set(key, merged[key]!)
  if (merged.dateYear) { params.set('date_from', `${merged.dateYear}-01-01`); params.set('date_to', `${merged.dateYear}-12-31`) }
  return params
}

export const api = {
  async getOverview(): Promise<Overview> {
    const data = await request<{ valid_records: number; cities: number; majors: number; latest_year: number; articles: number; needs_review: number; last_sync: string | null }>('/api/dashboard')
    return { records: data.valid_records, cities: data.cities, majors: data.majors, latestYear: data.latest_year, articles: data.articles, needsReview: data.needs_review, lastSync: data.last_sync }
  },
  async getRecords(): Promise<ExperienceRecord[]> {
    const data = await request<{ results: RawRecord[] }>('/api/records?limit=10000')
    return data.results.map(toRecord)
  },
  async searchRecords(query: string, filters?: SearchFilters, priority: Facet[] = []): Promise<SearchResponse> {
    const started = performance.now()
    const merged = filters ?? {}
    const params = searchParameters(query, filters)
    params.set('limit', '10000')
    const data = await request<{ results: RawRecord[]; summary: AnalyticsSummary }>(`/api/search?${params}`)
    const records = data.results.map(toRecord)
    if (priority.length) records.sort((a, b) => {
      const score = (record: ExperienceRecord) => priority.reduce((total, key, index) => {
        const field = key === 'dateYear' ? record.date.slice(0, 4) : String(record[key])
        return total + (merged[key] && field.includes(merged[key]!) ? priority.length - index : 0)
      }, 0)
      return score(b) - score(a) || b.date.localeCompare(a.date)
    })
    return { records, total: records.length, elapsedMs: Math.round(performance.now() - started), analysis: data.summary }
  },
  getAnalytics: (dimensions: string[]) => request<AnalyticsResponse>(`/api/analytics?dimensions=${encodeURIComponent(dimensions.join(','))}`),
  authStatus: () => request<AuthStatus>('/api/auth/status'),
  openLogin: (rememberLogin?: boolean) => request<AuthStatus>('/api/auth/start', json(rememberLogin === undefined ? {} : { remember_login: rememberLogin })),
  confirmLogin: () => request<AuthStatus>('/api/auth/confirm', { method: 'POST' }),
  cancelLogin: () => request<AuthStatus>('/api/auth/cancel', { method: 'POST' }),
  saveAuthPreferences: (rememberLogin: boolean) => request<{ remember_login: boolean }>('/api/auth/preferences', { method: 'PUT', body: JSON.stringify({ remember_login: rememberLogin }) }),
  syncStatus: () => request<JobStatus>('/api/sync/status'),
  startSync: (mode: 'test' | 'full') => request<JobStatus>('/api/sync/start', json({ mode, max_pages: mode === 'full' ? 1000 : 2 })),
  ensureData: () => request<{ started: boolean; stage?: 'sync' | 'process' }>('/api/sync/ensure', { method: 'POST' }),
  retrySync: () => request<JobStatus>('/api/sync/retry', { method: 'POST' }),
  resumeSync: () => request<JobStatus>('/api/sync/start', json({ mode: 'resume', max_pages: 1000 })),
  exportUrl: (query: string, filters: SearchFilters) => `/api/export?${searchParameters(query, filters)}`,
  processStatus: () => request<JobStatus>('/api/process/status'),
  startProcess: (allLocal: boolean) => request<JobStatus>('/api/process/start', json({ all_local: allLocal, build_index: false })),
  getSettings: () => request<PortalSettings>('/api/settings'),
  saveSettings: (values: Partial<PortalSettings>) => request<PortalSettings>('/api/settings', { method: 'PUT', body: JSON.stringify({ values }) }),
}
