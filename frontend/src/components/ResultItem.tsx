import { motion } from 'framer-motion'
import { ChevronRight, MapPin } from 'lucide-react'
import type { ExperienceRecord } from '../types'

export function ResultItem({ record, index, onOpen }: { record: ExperienceRecord; index: number; onOpen: (record: ExperienceRecord) => void }) {
  return <motion.article layout initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.31, delay: Math.min(index, 10) * 0.055 }} className="result-item" onClick={() => onOpen(record)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(record) } }} role="button" tabIndex={0} aria-label={`查看${record.person}的选调经验详情`}>
    <div className="result-index"><span>{String(index + 1).padStart(2, '0')}</span></div>
    <div className="result-body"><h3>{record.person}{record.needsReview && <span className="result-review">待核对</span>}<ChevronRight size={17} /></h3><p className="result-mainline"><strong>{record.year ? `${record.year}届` : '届别待核对'}</strong><span>·</span>{record.major}<span>·</span><MapPin size={13} /> {record.city}<span>·</span>{record.position}</p></div>
  </motion.article>
}
