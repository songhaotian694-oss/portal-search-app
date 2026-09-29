import { useEffect, useMemo, useState } from 'react'
import type { EChartsOption } from 'echarts'
import { ArrowRight, ChartNoAxesCombined, GitBranch, MoveUpRight, RotateCcw } from 'lucide-react'
import { motion } from 'framer-motion'
import type { AnalyticsResponse, AnalyticsSummary, ExperienceRecord } from '../types'
import { ChartContainer } from './ChartContainer'
import { api } from '../services/api'

type Dimension = 'major' | 'city' | 'position' | 'year' | 'dateYear' | 'degree'
type View = 'relation' | 'trend' | 'region'
const dimensions: { value: Dimension; label: string }[] = [
  { value: 'major', label: '专业' }, { value: 'city', label: '地区' }, { value: 'position', label: '岗位' }, { value: 'year', label: '届别' }, { value: 'dateYear', label: '收录年份' }, { value: 'degree', label: '学历' },
]
const colors = ['#203f5d', '#2b7b96', '#787fa8']
const read = (record: ExperienceRecord, key: Dimension) => key === 'year' ? (record.year ? `${record.year} 届` : '待核对') : key === 'dateYear' ? (record.date.slice(0, 4) || '待核对') : record[key]

function relationOption(analytics: AnalyticsResponse, selected: string | null, dims: Dimension[]): EChartsOption {
  const prominent = new Set(dims.flatMap(dim => analytics.relations.nodes
    .filter(node => node.dimension === dim)
    .sort((a, b) => b.count - a.count)
    .slice(0, dim === 'position' ? 6 : 8)
    .map(node => `${node.dimension}|${node.value}`)))
  const links = analytics.relations.links
    .filter(link => prominent.has(`${link.fromDimension}|${link.fromValue}`) && prominent.has(`${link.toDimension}|${link.toValue}`))
    .map(link => ({ source: `${link.fromDimension}|${link.fromValue}`, target: `${link.toDimension}|${link.toValue}`, value: link.count }))
  const connected = new Set(links.flatMap(link => [link.source, link.target]))
  const nodes = analytics.relations.nodes.filter(node => connected.has(`${node.dimension}|${node.value}`)).map(node => {
    const name = `${node.dimension}|${node.value}`
    return { name, value: node.count, itemStyle: { color: colors[dims.indexOf(node.dimension as Dimension)], opacity: selected && selected !== name ? 0.62 : 1 } }
  })
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: (params: unknown) => { const p = params as { name?: string; value?: number }; return `${p.name?.split('|')[1] || ''}<br/>${p.value ?? ''} 条关联` } },
    animationDuration: 650, animationDurationUpdate: 420,
    series: [{ type: 'sankey', data: nodes, links, left: 18, right: 90, top: 20, bottom: 22, nodeWidth: 13, nodeGap: 12, draggable: false, layoutIterations: 24, emphasis: { focus: 'adjacency' }, lineStyle: { color: 'gradient', curveness: 0.53, opacity: 0.34 }, label: { color: '#263c52', fontSize: 11, formatter: (params: { name: string }) => params.name.split('|')[1] } }],
  }
}

function barOption(summary: AnalyticsSummary, dimension: Dimension): EChartsOption {
  const values = (dimension === 'year' ? summary.years.slice().sort((a, b) => a[0].localeCompare(b[0])) : summary.cities).slice(0, 10)
  return {
    backgroundColor: 'transparent',
    grid: { left: 18, right: 20, top: 30, bottom: 60, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: values.map(v => v[0]), axisTick: { show: false }, axisLabel: { color: '#687a89', interval: 0, rotate: values.length > 6 ? 35 : 0, fontSize: 11 }, axisLine: { lineStyle: { color: '#d8e0e5' } } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#e8edef', type: 'dashed' } }, axisLabel: { color: '#8998a4' } },
    animationDuration: 680, animationDurationUpdate: 400,
    series: [{ type: 'bar', data: values.map(v => v[1]), barMaxWidth: 38, itemStyle: { color: dimension === 'year' ? '#273f65' : '#317b94', borderRadius: [3, 3, 0, 0] }, emphasis: { itemStyle: { color: '#786eaa' } } }],
  }
}

export function DataExplorer({ records, onSearch }: { records: ExperienceRecord[]; onSearch: (query: string) => void }) {
  const [view, setView] = useState<View>('relation')
  const [dims, setDims] = useState<Dimension[]>(['major', 'city', 'position'])
  const [selected, setSelected] = useState<string | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null)
  const [error, setError] = useState('')
  const dimensionKey = dims.join(',')
  useEffect(() => {
    let cancelled = false
    setAnalytics(null)
    void api.getAnalytics(dims).then(data => { if (!cancelled) { setAnalytics(data); setError('') } }).catch(cause => { if (!cancelled) setError((cause as Error).message) })
    return () => { cancelled = true }
  }, [dimensionKey])
  const selectedRecords = useMemo(() => selected ? records.filter(record => read(record, selected.split('|')[0] as Dimension) === selected.split('|')[1]) : records, [records, selected])
  const option = useMemo(() => analytics ? (view === 'relation' ? relationOption(analytics, selected, dims) : barOption(analytics.summary, view === 'trend' ? 'year' : 'city')) : {}, [analytics, selected, dimensionKey, view])
  const nodeName = selected?.split('|')[1]
  const selectedFacet = selected?.split('|')[0]
  function chooseNode(name: string) {
    if (view === 'relation') setSelected(current => current === name ? null : name)
    else setSelected(`${view === 'trend' ? 'year' : 'city'}|${view === 'trend' ? `${name} 届` : name}`)
  }
  function chooseDimension(index: number, value: Dimension) {
    setDims(current => { if (current.includes(value) && current[index] !== value) return current; const next = [...current]; next[index] = value; return next })
    setSelected(null)
  }
  return <div className="explorer-layout"><div className="explorer-main"><div className="explorer-toolbar"><div className="explorer-tabs" role="tablist" aria-label="可视化类型"><button role="tab" aria-selected={view === 'relation'} className={view === 'relation' ? 'active' : ''} onClick={() => setView('relation')}><GitBranch size={16} /> 关系网络</button><button role="tab" aria-selected={view === 'trend'} className={view === 'trend' ? 'active' : ''} onClick={() => setView('trend')}><ChartNoAxesCombined size={16} /> 届别趋势</button><button role="tab" aria-selected={view === 'region'} className={view === 'region' ? 'active' : ''} onClick={() => setView('region')}>地区分布</button></div></div>
    {view === 'relation' && <div className="dimension-row"><span>关系路径</span>{dims.map((dim, index) => <span className="dimension-step" key={index}>{index > 0 && <ArrowRight size={15} />}<select value={dim} aria-label={`第${index + 1}层维度`} onChange={event => chooseDimension(index, event.target.value as Dimension)}>{dimensions.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></span>)}</div>}
    {error ? <p className="workspace-message">{error}</p> : analytics ? <div className={`explorer-chart ${view === 'relation' ? 'relation-chart' : ''}`}><ChartContainer option={option} onClick={chooseNode} height={Math.max(420, Math.min(540, records.length * 16))} /></div> : <p className="workspace-message">图表加载中…</p>}<div className="chart-legend"><span><i style={{ background: colors[0] }} /> 起点</span><span><i style={{ background: colors[1] }} /> 关联</span><span><i style={{ background: colors[2] }} /> 终点</span></div></div>
    <aside className="explorer-side"><h2>{selected ? nodeName : '关联记录'}</h2>{selected && <button className="clear-node" onClick={() => setSelected(null)}><RotateCcw size={14} /> 清除选择</button>}
      <div className="node-count"><strong>{selectedRecords.length}</strong><span>条记录</span></div><div className="node-mini-list"><div className="node-mini-head">相关记录</div>{selectedRecords.slice(0, 4).map((record, index) => <motion.button layout key={record.id} onClick={() => onSearch(`${record.year ? `${record.year}届 ` : ''}${record.major} ${record.city}`)}><span>0{index + 1}</span><div><strong>{record.person}</strong><small>{record.major} · {record.city}</small></div><MoveUpRight size={14} /></motion.button>)}</div>{selected && <button className="node-search" onClick={() => onSearch(selectedFacet === 'dateYear' ? `${nodeName}年收录的选调经验` : `${nodeName} 选调经验`)}>查看检索结果 <ArrowRight size={16} /></button>}</aside></div>
}
