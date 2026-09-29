import { useMemo, useState, type FormEvent } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, ChevronDown, MessageCircle, Send, Sparkles, TrendingUp } from 'lucide-react'
import type { ExperienceRecord, SearchFilters } from '../types'

function rank(values: string[]): [string, number][] {
  const count = new Map<string, number>()
  values.forEach(value => count.set(value, (count.get(value) || 0) + 1))
  return [...count].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-CN'))
}

export function InsightPanel({ records, onFacet }: { records: ExperienceRecord[]; onFacet: (filter: SearchFilters) => void }) {
  const [chatOpen, setChatOpen] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [question, setQuestion] = useState('')
  const summary = useMemo(() => ({ cities: rank(records.map(record => record.city)), positions: rank(records.map(record => record.position)), majors: rank(records.map(record => record.major)), years: rank(records.map(record => String(record.year))) }), [records])
  const topCity = summary.cities[0]
  const topRole = summary.positions[0]
  const note = records.length ? `${topCity?.[0] ?? '当前地区'}出现 ${topCity?.[1] ?? 0} 条记录；${topRole?.[0] ?? '相关岗位'}是当前范围内较常见的方向。` : '调整查询条件后，这里会显示当前结果的结构性线索。'
  function ask(event: FormEvent) { event.preventDefault(); if (prompt.trim()) { setQuestion(prompt.trim()); setPrompt('') } }
  return <aside className="insight-panel"><div className="insight-head"><span className="insight-symbol"><Sparkles size={18} /></span><div><small>INSIGHT ENGINE</small><h2>智能洞察</h2></div><span className="insight-live"><i /> LIVE</span></div><div className="insight-intro">基于当前筛选结果自动更新 <span>· 演示分析</span></div>
    <section className="insight-summary"><div className="insight-section-label"><span>01 / 摘要</span><TrendingUp size={15} /></div><strong>{records.length} <small>条匹配记录</small></strong><p>{note}</p></section>
    <section className="insight-section"><div className="insight-section-label"><span>02 / 高频地区</span><small>TOP 3</small></div>{summary.cities.slice(0, 3).map(([name, count], index) => <button className="insight-rank" key={name} onClick={() => onFacet({ city: name })}><span>0{index + 1}</span><strong>{name}</strong><i><b style={{ width: `${records.length ? (count / records.length) * 100 : 0}%` }} /></i><small>{count}</small></button>)}{!records.length && <p className="insight-muted">暂无可分析地区</p>}</section>
    <section className="insight-section"><div className="insight-section-label"><span>03 / 岗位方向</span><small>TOP 3</small></div>{summary.positions.slice(0, 3).map(([name, count]) => <button className="role-row" key={name} onClick={() => onFacet({ position: name })}><span>{name}</span><small>{count} 条 <ArrowRight size={13} /></small></button>)}</section>
    <section className="insight-section insight-distribution"><div className="insight-section-label"><span>04 / 专业分布</span><small>{summary.majors.length} 类</small></div><div className="distribution-strip">{summary.majors.slice(0, 5).map(([name, count], index) => <button title={`${name} · ${count} 条`} aria-label={`筛选${name}`} key={name} onClick={() => onFacet({ major: name })} style={{ width: `${Math.max(8, records.length ? (count / records.length) * 100 : 0)}%`, backgroundColor: ['#1d4b69', '#2c7792', '#6f88a0', '#8888aa', '#b0b6c4'][index] }} />)}</div><div className="distribution-labels">{summary.majors.slice(0, 2).map(([name, count]) => <span key={name}>{name} <b>{count}</b></span>)}</div></section>
    <section className="insight-section"><div className="insight-section-label"><span>05 / 届别趋势</span><small>2023 — 2025</small></div><div className="year-spark">{['2023', '2024', '2025'].map(year => { const count = summary.years.find(([name]) => name === year)?.[1] || 0; return <button key={year} onClick={() => onFacet({ year })} title={`${year} 届 ${count} 条`}><span style={{ height: `${Math.max(8, records.length ? (count / records.length) * 140 : 0)}px` }} /><small>{year}</small></button> })}</div></section>
    <div className="insight-observation"><span>值得注意</span><p>{records.length > 0 && summary.majors.length > 1 ? `当前样本涉及 ${summary.majors.length} 个专业方向。点击图表元素可直接缩小结果范围。` : '可从地区、岗位或专业继续细化探索。'}</p></div>
    <div className="insight-chat"><button className="chat-toggle" onClick={() => setChatOpen(open => !open)} aria-expanded={chatOpen}><span><MessageCircle size={16} /> 继续提问</span><ChevronDown size={15} className={chatOpen ? 'rotated' : ''} /></button><AnimatePresence>{chatOpen && <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="chat-body"><p>基于当前演示结果提问，回复为本地模板分析。</p>{question && <div className="chat-answer"><small>你问：{question}</small><span>当前匹配 {records.length} 条记录，主要集中在 {topCity?.[0] ?? '暂无地区'}，其中 {topRole?.[0] ?? '暂无岗位'}较常见。可点击上方统计进一步筛选。</span></div>}<form onSubmit={ask}><input value={prompt} onChange={event => setPrompt(event.target.value)} aria-label="向洞察面板提问" placeholder="例如：哪些岗位更集中？" /><button aria-label="发送问题" disabled={!prompt.trim()}><Send size={15} /></button></form></motion.div>}</AnimatePresence></div>
  </aside>
}
