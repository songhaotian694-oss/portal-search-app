import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { ArrowDownRight, ArrowUpRight, CircleDot, DatabaseZap, MoveUpRight } from 'lucide-react'
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

function NetworkIllustration() {
  return <div className="hero-network" aria-hidden="true"><svg viewBox="0 0 440 270" fill="none"><path d="M35 188L122 80L225 143L307 48L399 102M122 80L181 216L307 48M225 143L366 225L399 102M35 188L181 216L366 225" stroke="#cbd5dc" strokeWidth="1"/><path d="M122 80L225 143L307 48" stroke="#287f9a" strokeWidth="2"/><circle cx="35" cy="188" r="6" fill="#b4c9cf"/><circle cx="122" cy="80" r="10" fill="#287f9a"/><circle cx="225" cy="143" r="15" fill="#142d46"/><circle cx="307" cy="48" r="7" fill="#7d83ac"/><circle cx="399" cy="102" r="6" fill="#b4c9cf"/><circle cx="181" cy="216" r="6" fill="#b4c9cf"/><circle cx="366" cy="225" r="8" fill="#287f9a"/><text x="208" y="148" textAnchor="middle" fill="white" fontSize="11">QUERY</text><text x="90" y="53" fill="#698296" fontSize="10" letterSpacing="2">MAJOR</text><text x="314" y="34" fill="#698296" fontSize="10" letterSpacing="2">CITY</text><text x="369" y="252" fill="#698296" fontSize="10" letterSpacing="2">ROLE</text></svg></div>
}

export function HomePage({ onSearch }: { onSearch: (query: string, priority?: Facet[]) => void }) {
  const [overview, setOverview] = useState<Overview>({ records: 0, cities: 0, majors: 0, latestYear: 2025 })
  useEffect(() => { void api.getOverview().then(setOverview) }, [])
  return <div className="home-page">
    <section className="hero-section">
      <div className="hero-left">
        <div className="section-index"><span className="index-line" /> 01 / KNOWLEDGE INTELLIGENCE <span className="index-pulse" /></div>
        <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.42 }}>让每一次搜索，<br />都成为<span>新的发现。</span></motion.h1>
        <p className="hero-deck">从一句自然语言开始，穿过专业、地区与岗位之间的关联，找到值得进一步阅读的选调经验线索。</p>
        <div className="hero-line-link"><Link to="/explore">浏览数据关系 <MoveUpRight size={18} /></Link><span>01 — 03</span></div>
        <div className="hero-meta"><span><CircleDot size={14} /> 选调生经验信息</span><span>研究型检索空间 / DEMO</span></div>
      </div>
      <div className="hero-right"><div className="search-stage-head"><span>RESEARCH TERMINAL</span><span>输入问题，系统会提取条件</span></div><SmartSearch onSubmit={onSearch} /><div className="search-stage-foot"><span>自然语言 → 条件识别 → 关联结果</span><ArrowDownRight size={17} /></div></div>
    </section>
    <section className="home-lower">
      <div className="overview-block"><div className="eyebrow"><DatabaseZap size={15} /> DATASET / 01</div><h2>不是信息堆叠，<br />而是可追踪的脉络。</h2><p>当前为交互演示数据。真实数据接入后，所有记录可回到来源与证据。</p><NetworkIllustration /></div>
      <div className="metrics-block"><div className="metrics-top"><span>数据概况 <small>LIVE SNAPSHOT</small></span><Link to="/explore" aria-label="探索数据"><ArrowUpRight size={18} /></Link></div><div className="metric-grid"><Link to="/search" aria-label="查看全部记录"><small>记录样本</small><strong><CountUp value={overview.records} /></strong><span>RECORDS</span></Link><Link to="/explore" aria-label="探索覆盖城市"><small>覆盖城市</small><strong><CountUp value={overview.cities} /></strong><span>CITIES</span></Link><Link to="/explore" aria-label="探索专业方向"><small>专业方向</small><strong><CountUp value={overview.majors} /></strong><span>MAJORS</span></Link><Link to={`/search?q=${overview.latestYear}%E5%B1%8A`} aria-label={`查看${overview.latestYear}届记录`}><small>最新届别</small><strong><CountUp value={overview.latestYear} /></strong><span>COHORT</span></Link></div><div className="metrics-note"><span className="status-dot" /> 本页面展示模拟数据，不代表真实统计</div></div>
      <div className="principle-block"><span>探索路径 / HOW IT WORKS</span><ol><li><b>01</b><div><strong>用问题定义范围</strong><small>自然语言会拆解成可调整的条件。</small></div></li><li><b>02</b><div><strong>在线索中浏览</strong><small>按地区、专业与岗位关联查看。</small></div></li><li><b>03</b><div><strong>回到证据</strong><small>从洞察打开具体记录与来源。</small></div></li></ol></div>
    </section>
  </div>
}
