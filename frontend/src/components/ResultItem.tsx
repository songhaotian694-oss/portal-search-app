import { ChevronRight, MapPin } from 'lucide-react'
import type { ExperienceRecord } from '../types'

export function ResultItem({ record, index, onOpen }: { record: ExperienceRecord; index: number; onOpen: (record: ExperienceRecord) => void }) {
  return <article className="result-item" onClick={() => onOpen(record)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(record) } }} role="button" tabIndex={0} aria-label={`查看${record.person}的选调经验详情`}>
    <div className="result-index"><span>{String(index + 1).padStart(2, '0')}</span></div>
    <div className="result-body"><h3>{record.person}<ChevronRight size={17} /></h3><p className="result-mainline"><strong>{record.year ? `${record.year}届` : '届别未提取'}</strong><span>·</span>{record.major}<span>·</span><MapPin size={13} /> {record.city}<span>·</span>{record.position}</p></div>
  </article>
}
