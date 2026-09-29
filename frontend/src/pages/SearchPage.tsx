import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowDownWideNarrow, CircleHelp, Layers3 } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { DetailDrawer } from '../components/DetailDrawer'
import { FilterPanel } from '../components/FilterPanel'
import { InsightPanel } from '../components/InsightPanel'
import { ResultList } from '../components/ResultList'
import { SmartSearch } from '../components/SmartSearch'
import { parseQuery, tokensToFilters } from '../lib/query'
import { api } from '../services/api'
import type { AnalyticsSummary, ExperienceRecord, Facet, SearchFilters } from '../types'

const emptyAnalysis: AnalyticsSummary = { total: 0, needsReview: 0, cities: [], positions: [], majors: [], years: [] }

export function SearchPage({ onSearch }: { onSearch: (query: string, priority?: Facet[]) => void }) {
  const [params] = useSearchParams()
  const query = params.get('q') || ''
  const priority = (params.get('priority') || '').split(',').filter((part): part is Facet => ['year', 'dateYear', 'major', 'city', 'type', 'degree', 'position'].includes(part))
  const priorityKey = priority.join(',')
  const [allRecords, setAllRecords] = useState<ExperienceRecord[]>([])
  const [records, setRecords] = useState<ExperienceRecord[]>([])
  const [analysis, setAnalysis] = useState<AnalyticsSummary>(emptyAnalysis)
  const [filters, setFilters] = useState<SearchFilters>(() => tokensToFilters(parseQuery(query)))
  const [selected, setSelected] = useState<ExperienceRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [sort, setSort] = useState<'relevance' | 'newest'>('relevance')
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => { void api.getRecords().then(setAllRecords).catch(cause => setError((cause as Error).message)) }, [])
  useEffect(() => { setFilters(tokensToFilters(parseQuery(query))) }, [query])
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    void api.searchRecords(query, filters, priority).then(response => {
      if (!cancelled) { setRecords(response.records); setAnalysis(response.analysis); setElapsed(response.elapsedMs); setLoading(false) }
    }).catch(cause => { if (!cancelled) { setError((cause as Error).message); setLoading(false) } })
    return () => { cancelled = true }
  }, [query, filters, priorityKey])
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80)
    onScroll(); window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  const sorted = useMemo(() => sort === 'newest' ? [...records].sort((a, b) => b.date.localeCompare(a.date)) : records, [records, sort])
  const active = Object.values(filters).filter(Boolean).length
  const applyFacet = (next: SearchFilters) => { setFilters(current => ({ ...current, ...next })); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  return <div className="search-page">
    <div className="search-page-heading"><span className="eyebrow">02 / SEARCH SPACE</span><h1>沿着线索，找到答案。</h1><p>每条结果都可以回到其专业、地区与岗位脉络。</p></div>
    <div className={`query-bar ${scrolled ? 'query-bar-small' : ''}`}><div className="query-bar-label"><span>QUERY BAR</span><strong>{query ? '当前问题' : '开始一个问题'}</strong></div><SmartSearch key={query + priorityKey} initialValue={query} initialPriority={priority} compact onSubmit={onSearch} /></div>
    <div className="results-toolbar"><div><span className="toolbar-pip" /> <strong>{loading ? '正在检索' : `${records.length} 条线索`}</strong><span>从 {allRecords.length} 条本地记录中找到 · {elapsed} ms</span></div><div className="toolbar-actions"><span><Layers3 size={15} /> {active} 个条件</span><label><ArrowDownWideNarrow size={15} /><select aria-label="排序方式" value={sort} onChange={event => setSort(event.target.value as typeof sort)}><option value="relevance">相关度优先</option><option value="newest">最新收录</option></select></label></div></div>
    {error && <p className="workspace-message" role="alert">{error}</p>}
    <div className="search-columns"><FilterPanel records={allRecords} filters={filters} onChange={setFilters} /><section className="result-column"><div className="result-column-note"><CircleHelp size={15} /><span>点击任意记录，右侧展开详情；列表位置将保留。</span></div><motion.div layout><ResultList records={sorted} loading={loading} onOpen={setSelected} /></motion.div></section><InsightPanel records={records} summary={analysis} onFacet={applyFacet} /></div>
    <DetailDrawer record={selected} onClose={() => setSelected(null)} />
  </div>
}
