import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, ArrowUpRight, Compass, Search, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { SmartSearch } from '../components/SmartSearch'
import { api } from '../services/api'
import type { Facet, Overview } from '../types'

const quickQueries = [
  { label: '北京', query: '北京', position: 'city' },
  { label: '计算机', query: '计算机', position: 'major' },
  { label: '2025届', query: '2025届', position: 'year' },
] as const

function CountUp({ value }: { value: number }) {
  const [display, setDisplay] = useState(0)
  const reduced = useReducedMotion()
  useEffect(() => {
    if (reduced) { setDisplay(value); return }
    const started = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / 720)
      setDisplay(Math.round(value * (1 - Math.pow(1 - progress, 3))))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [value, reduced])
  return <>{display}</>
}

function moveGlow(event: PointerEvent<HTMLDivElement>) {
  if (event.pointerType === 'touch') return
  const bounds = event.currentTarget.getBoundingClientRect()
  event.currentTarget.style.setProperty('--glow-x', `${event.clientX - bounds.left}px`)
  event.currentTarget.style.setProperty('--glow-y', `${event.clientY - bounds.top}px`)
}

export function HomePage({ onSearch }: { onSearch: (query: string, priority?: Facet[]) => void }) {
  const [overview, setOverview] = useState<Overview>({ records: 0, cities: 0, majors: 0, latestYear: 0, articles: 0, needsReview: 0, lastSync: null })
  const [error, setError] = useState('')
  const [committing, setCommitting] = useState(false)
  const pendingSearch = useRef<number | null>(null)
  const reduced = useReducedMotion()
  useEffect(() => { void api.getOverview().then(setOverview).catch(cause => setError((cause as Error).message)) }, [])
  useEffect(() => () => { if (pendingSearch.current !== null) window.clearTimeout(pendingSearch.current) }, [])
  const enter = (delay: number) => reduced ? {} : { initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] as const } }
  function submitSearch(query: string, priority: Facet[] = []) {
    if (pendingSearch.current !== null) return
    setCommitting(true)
    if (reduced) { onSearch(query, priority); return }
    pendingSearch.current = window.setTimeout(() => {
      pendingSearch.current = null
      onSearch(query, priority)
    }, 240)
  }

  return <div className="home-page home-page-glass">
    <section className="hero-section">
      <div className="hero-left">
        <motion.div {...enter(0.04)} className="home-heading">
          <span className="home-category"><span className="home-category-dot" />选调生信息</span>
          <h1>让每条经历<br /><span>都有迹可循</span></h1>
          <p className="hero-deck">检索选调经历与岗位信息，发现地区、专业和届别之间的联系。</p>
          <div className="home-actions">
            <Link className="home-action-primary" data-liquid to="/search">查看全部记录 <ArrowUpRight size={17} /></Link>
            <Link className="home-action-secondary" data-liquid to="/explore"><Compass size={16} />数据探索</Link>
          </div>
        </motion.div>
        <motion.div {...enter(0.2)} className="home-knowledge" aria-label="快捷检索线索">
          <div className="home-knowledge-head"><span>快捷检索</span><span>点击线索查看结果</span></div>
          <div className="home-knowledge-network">
            <svg viewBox="0 0 440 116" preserveAspectRatio="none" aria-hidden="true"><path d="M70 58 C145 58 158 27 220 58 S312 58 370 27" /><path d="M70 58 C145 58 160 89 220 58 S315 58 370 89" /><circle cx="220" cy="58" r="5" /></svg>
            {quickQueries.map(item => <motion.button key={item.query} type="button" data-liquid className={`home-knowledge-node home-node-${item.position}`} onClick={() => submitSearch(item.query)} whileHover={reduced ? undefined : { y: -4, scale: 1.04 }} whileTap={reduced ? undefined : { scale: 0.97 }} aria-label={`检索${item.label}`}>{item.label}<ArrowUpRight size={13} /></motion.button>)}
          </div>
        </motion.div>
      </div>
      <motion.div {...enter(0.12)} className="hero-right">
        <div className={`home-glass-search ${committing ? 'is-committing' : ''}`} onPointerMove={reduced ? undefined : moveGlow}>
          <div className="home-search-heading"><div><span className="home-search-icon"><Sparkles size={20} /></span><div><span className="home-search-kicker">SMART SEARCH</span><h2>智能检索</h2></div></div><span className="home-search-state"><i />可用</span></div>
          <SmartSearch onSubmit={submitSearch} />
          <div className="home-search-examples"><span>试试搜索</span>{quickQueries.map(item => <button type="button" data-liquid key={item.query} onClick={() => submitSearch(item.query)}><Search size={13} />{item.label}</button>)}</div>
        </div>
      </motion.div>
    </section>
    <motion.section {...enter(0.28)} className="home-summary" aria-label="数据概况">
      <div><span>有效记录</span><strong><CountUp value={overview.records} /></strong></div>
      <div><span>覆盖地区</span><strong><CountUp value={overview.cities} /></strong></div>
      <div><span>专业方向</span><strong><CountUp value={overview.majors} /></strong></div>
      <div><span>最近同步</span><strong className="home-sync-date">{overview.lastSync?.slice(0, 10) || '尚未同步'}</strong></div>
      <Link to="/workspace" data-liquid aria-label="前往数据更新">更新数据 <ArrowRight size={15} /></Link>
    </motion.section>
    {error && <p className="workspace-message" role="alert">{error}</p>}
  </div>
}
