import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { SmartSearch } from '../components/SmartSearch'
import { api } from '../services/api'
import type { Facet, Overview } from '../types'

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

export function HomePage({ onSearch }: { onSearch: (query: string, priority?: Facet[]) => void }) {
  const [overview, setOverview] = useState<Overview>({ records: 0, cities: 0, majors: 0, latestYear: 0, articles: 0, needsReview: 0, lastSync: null })
  const [error, setError] = useState('')
  useEffect(() => { void api.getOverview().then(setOverview).catch(cause => setError((cause as Error).message)) }, [])
  return <div className="home-page home-page-simple">
    <section className="hero-section">
      <div className="hero-left">
        <span className="home-category">选调生信息</span>
        <h1>查找经历与岗位信息</h1>
        <p className="hero-deck">按地区、专业、届别或岗位检索，查看整理后的记录和来源。</p>
        <div className="home-actions"><Link to="/search">查看全部记录</Link><Link to="/explore">数据探索</Link></div>
      </div>
      <div className="hero-right"><SmartSearch onSubmit={onSearch} /></div>
    </section>
    <section className="home-summary" aria-label="数据概况">
      <div><span>有效记录</span><strong><CountUp value={overview.records} /></strong></div>
      <div><span>覆盖地区</span><strong><CountUp value={overview.cities} /></strong></div>
      <div><span>专业方向</span><strong><CountUp value={overview.majors} /></strong></div>
      <div><span>最近同步</span><strong className="home-sync-date">{overview.lastSync?.slice(0, 10) || '尚未同步'}</strong></div>
      <Link to="/workspace">更新数据 →</Link>
    </section>
    {error && <p className="workspace-message" role="alert">{error}</p>}
  </div>
}
