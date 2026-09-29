import { motion } from 'framer-motion'
import { ArrowUpRight, ChevronRight, MapPin } from 'lucide-react'
import type { ExperienceRecord } from '../types'

export function ResultItem({ record, index, onOpen }: { record: ExperienceRecord; index: number; onOpen: (record: ExperienceRecord) => void }) {
  return <motion.article layout initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.31, delay: Math.min(index, 10) * 0.055 }} className="result-item" onClick={() => onOpen(record)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(record) } }} role="button" tabIndex={0} aria-label={`查看${record.person}的选调经验详情`}>
    <div className="result-index"><span>{String(index + 1).padStart(2, '0')}</span><i /></div>
    <div className="result-body"><div className="result-kicker"><span>{record.year} 届 / {record.degree}</span><span className="result-dot" /><span>{record.type}</span></div><h3>{record.person}<ChevronRight size={17} /></h3><p className="result-mainline"><strong>{record.major}</strong><span>—</span><MapPin size={13} /> {record.city}<span>—</span>{record.position}</p><p className="result-excerpt">{record.excerpt}</p><div className="result-expand"><span>{record.organization} · {record.date} 收录 · 查看完整经历</span><ArrowUpRight size={15} /></div></div>
    <div className="result-side"><span className="relevance-label">RELEVANCE</span><strong>{record.confidence}<small>%</small></strong><div className="relevance-track"><i style={{ width: `${record.confidence}%` }} /></div><span className="source-label">{record.source}</span><small>{record.date}</small></div>
  </motion.article>
}
