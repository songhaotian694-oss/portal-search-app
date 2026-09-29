import { useEffect, useState, type FormEvent, type KeyboardEvent } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Command, GripVertical, Search, Sparkles, X } from 'lucide-react'
import { parseQuery } from '../lib/query'
import type { Facet, QueryToken } from '../types'

const examples = ['2025届计算机专业在北京的选调经验', '上海地区的数据分析岗位', '2024届公共管理专业去向']

export function SmartSearch({ initialValue = '', initialPriority = [], compact = false, onSubmit }: { initialValue?: string; initialPriority?: Facet[]; compact?: boolean; onSubmit: (query: string, priority: Facet[]) => void }) {
  const [value, setValue] = useState(initialValue)
  const [priority, setPriority] = useState<string[]>(initialPriority)
  const [dragging, setDragging] = useState<string | null>(null)
  useEffect(() => setValue(initialValue), [initialValue])
  useEffect(() => setPriority(initialPriority), [initialPriority.join(',')])
  const parsed = parseQuery(value)
  const tokens = [...parsed].sort((a, b) => {
    const ai = priority.indexOf(a.facet)
    const bi = priority.indexOf(b.facet)
    return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi)
  })
  function submit(event: FormEvent) { event.preventDefault(); if (value.trim()) onSubmit(value.trim(), tokens.map(token => token.facet)) }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); if (value.trim()) onSubmit(value.trim(), tokens.map(token => token.facet)) }
  }
  function removeToken(token: QueryToken) { setValue(current => current.replace(token.value, '').replace(/\s{2,}/g, ' ').trim()) }
  function dropToken(target: string) {
    if (!dragging || dragging === target) return
    const order = tokens.map(token => token.facet)
    const from = order.indexOf(dragging as Facet)
    const to = order.indexOf(target as Facet)
    order.splice(to, 0, order.splice(from, 1)[0])
    setPriority(order)
    setDragging(null)
  }
  return (
    <form className={`smart-search ${compact ? 'smart-search-compact' : ''}`} onSubmit={submit}>
      <div className="smart-topline"><span><Command size={15} /> INTELLIGENT QUERY</span><span className="smart-live"><i /> 实时解析</span></div>
      <div className="smart-input-wrap"><Search size={23} strokeWidth={1.6} /><textarea aria-label="自然语言检索" value={value} onChange={event => setValue(event.target.value)} onKeyDown={keyDown} rows={compact ? 1 : 2} placeholder="描述你想发现的信息…" /><span className="key-hint">↵</span></div>
      <div className="smart-token-zone" aria-live="polite">
        <span className="token-intro">{tokens.length ? '已识别条件' : '输入后自动识别查询条件'}</span>
        <AnimatePresence mode="popLayout">
          {tokens.map((token, index) => <motion.span layout initial={{ opacity: 0, scale: 0.88 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.88 }} transition={{ type: 'spring', stiffness: 420, damping: 30 }} key={token.facet} className={`query-token token-${token.facet}`} draggable onDragStart={() => setDragging(token.facet)} onDragOver={event => event.preventDefault()} onDrop={() => dropToken(token.facet)} onDragEnd={() => setDragging(null)} title="拖动可调整条件优先级">
            <GripVertical size={12} className="token-grip" /><em>{index + 1}</em><b>{token.label}</b><span>{token.value}</span><button type="button" aria-label={`移除${token.label}${token.value}`} onClick={() => removeToken(token)}><X size={12} /></button>
          </motion.span>)}
        </AnimatePresence>
      </div>
      {!compact && <div className="example-queries"><span>试试这样提问</span>{examples.map(example => <button key={example} type="button" onClick={() => setValue(example)}>{example}<ArrowRight size={13} /></button>)}</div>}
      <div className="smart-bottom"><span><Sparkles size={14} /> 支持自然语言 · Enter 发起检索</span><button className="primary-action" type="submit" disabled={!value.trim()}>开始探索 <ArrowRight size={17} /></button></div>
    </form>
  )
}
