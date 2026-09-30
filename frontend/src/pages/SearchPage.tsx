import { useEffect, useMemo, useState } from 'react'
import { ArrowDownToLine, ArrowDownWideNarrow } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { DetailDrawer } from '../components/DetailDrawer'
import { FilterPanel } from '../components/FilterPanel'
import { ResultList } from '../components/ResultList'
import { SmartSearch } from '../components/SmartSearch'
import { api } from '../services/api'
import type { ExperienceRecord, Facet, SearchFilters } from '../types'

export function SearchPage({ onSearch }: { onSearch: (query: string, priority?: Facet[]) => void }) {
  const [params] = useSearchParams()
  const query = params.get('q') || ''
  const priority = (params.get('priority') || '').split(',').filter((part): part is Facet => ['year', 'dateYear', 'major', 'city', 'type', 'degree', 'position'].includes(part))
  const priorityKey = priority.join(',')
  const [allRecords, setAllRecords] = useState<ExperienceRecord[]>([])
  const [records, setRecords] = useState<ExperienceRecord[]>([])
  const [filters, setFilters] = useState<SearchFilters>({})
  const [selected, setSelected] = useState<ExperienceRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sort, setSort] = useState<'relevance' | 'newest'>('relevance')
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => { void api.getRecords().then(setAllRecords).catch(cause => setError((cause as Error).message)) }, [])
  useEffect(() => { setFilters({}) }, [query])
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    void api.searchRecords(query, filters, priority).then(response => {
      if (!cancelled) { setRecords(response.records); setLoading(false) }
    }).catch(cause => { if (!cancelled) { setError((cause as Error).message); setLoading(false) } })
    return () => { cancelled = true }
  }, [query, filters, priorityKey])
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80)
    onScroll(); window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  const sorted = useMemo(() => sort === 'newest' ? [...records].sort((a, b) => b.date.localeCompare(a.date)) : records, [records, sort])
  return <div className="search-page">
    <div className="search-page-heading"><h1>信息检索</h1></div>
    <div className={`query-bar ${scrolled ? 'query-bar-small' : ''}`}><SmartSearch key={query + priorityKey} initialValue={query} initialPriority={priority} compact onSubmit={onSearch} /></div>
    <div className="results-toolbar"><div><strong>{loading ? '正在检索' : `${records.length} 条结果`}</strong></div><div className="toolbar-actions"><a className="search-export" href={loading || error ? undefined : api.exportUrl(query, filters)} aria-disabled={loading || !!error}><ArrowDownToLine size={15} /> 导出当前结果</a><label><ArrowDownWideNarrow size={15} /><select aria-label="排序方式" value={sort} onChange={event => setSort(event.target.value as typeof sort)}><option value="relevance">相关度优先</option><option value="newest">最新收录</option></select></label></div></div>
    {error && <p className="workspace-message" role="alert">{error}</p>}
    <div className="search-columns"><FilterPanel records={allRecords} filters={filters} onChange={setFilters} /><section className="result-column"><ResultList records={sorted} loading={loading} onOpen={setSelected} /></section></div>
    <DetailDrawer record={selected} onClose={() => setSelected(null)} />
  </div>
}
