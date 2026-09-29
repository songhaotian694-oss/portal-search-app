import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, ScanSearch, Sparkles } from 'lucide-react'
import { parseQuery } from '../lib/query'

export function QueryParser({ query, onComplete }: { query: string | null; onComplete: () => void }) {
  const [visible, setVisible] = useState(0)
  const reduced = useReducedMotion()
  const tokens = parseQuery(query ?? '')
  useEffect(() => {
    if (!query) return
    setVisible(0)
    const timers = tokens.map((_, index) => window.setTimeout(() => setVisible(index + 1), reduced ? 40 : 220 + index * 180))
    timers.push(window.setTimeout(onComplete, reduced ? 280 : 1150))
    return () => timers.forEach(clearTimeout)
  }, [query, onComplete, reduced, tokens.length])
  return <AnimatePresence>{query && <motion.div className="parser-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.24 }} role="status" aria-live="polite">
    <motion.div className="parser-sheet" initial={{ y: 18, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -10, opacity: 0 }} transition={{ duration: 0.34 }}>
      <div className="parser-kicker"><ScanSearch size={17} /> QUERY UNDERSTANDING <span>01 / 02</span></div>
      <p>正在理解你的问题</p><h2>“{query}”</h2>
      <div className="parser-track"><span className="parser-track-line" /><span className="parser-source"><Sparkles size={16} /> 查询</span><ArrowRight size={18} className="parser-arrow" /><div className="parser-nodes">
        {tokens.length ? tokens.map((token, index) => <motion.span key={token.facet} className="parser-node" initial={{ opacity: 0, y: 10, scale: 0.92 }} animate={{ opacity: index < visible ? 1 : 0.25, y: index < visible ? 0 : 10, scale: index < visible ? 1 : 0.92 }} transition={{ type: 'spring', stiffness: 360, damping: 27 }}><small>{token.label}</small>{token.value}</motion.span>) : <motion.span className="parser-node" animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 0.8 }}>关键词检索</motion.span>}
      </div></div>
      <div className="parser-progress"><span style={{ width: `${Math.max(12, (visible / Math.max(tokens.length, 1)) * 100)}%` }} /></div><small className="parser-foot">条件将自动汇入结果页 · 演示数据</small>
    </motion.div>
  </motion.div>}</AnimatePresence>
}
