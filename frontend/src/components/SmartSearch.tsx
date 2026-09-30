import { useEffect, useState, type FormEvent, type KeyboardEvent } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, GripVertical, Search, X } from 'lucide-react'
import { parseQuery } from '../lib/query'
import type { Facet, QueryToken } from '../types'

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
  function removeToken(token: QueryToken) { setValue(current => (token.sources || [token.value]).reduce((text, source) => text.replaceAll(source, ''), current.normalize('NFKC')).replace(/\s{2,}/g, ' ').trim()) }
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
      <div className="smart-input-wrap"><Search size={23} strokeWidth={1.6} /><textarea aria-label="搜索选调生信息" value={value} onChange={event => setValue(event.target.value)} onKeyDown={keyDown} rows={compact ? 1 : 2} placeholder="搜索地区、专业、届别或岗位" /></div>
      {tokens.length > 0 && <div className="smart-token-zone" aria-live="polite">
        <AnimatePresence mode="popLayout">
          {tokens.map(token => <motion.span layout initial={{ opacity: 0, scale: 0.88 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.88 }} transition={{ type: 'spring', stiffness: 420, damping: 30 }} key={token.facet} className={`query-token token-${token.facet}`} draggable onDragStart={() => setDragging(token.facet)} onDragOver={event => event.preventDefault()} onDrop={() => dropToken(token.facet)} onDragEnd={() => setDragging(null)} title="拖动可调整条件优先级">
            <GripVertical size={12} className="token-grip" /><b>{token.label}</b><span>{token.value}</span><button type="button" aria-label={`移除${token.label}${token.value}`} onClick={() => removeToken(token)}><X size={12} /></button>
          </motion.span>)}
        </AnimatePresence>
      </div>}
      <div className="smart-bottom"><button className="primary-action" data-liquid type="submit" disabled={!value.trim()}>搜索 <ArrowRight size={17} /></button></div>
    </form>
  )
}
