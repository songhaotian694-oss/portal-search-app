import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { RotateCcw, SlidersHorizontal } from 'lucide-react'
import type { ExperienceRecord, SearchFilters } from '../types'

type FilterKey = keyof SearchFilters
const sections: { key: FilterKey; label: string; pick: (record: ExperienceRecord) => string }[] = [
  { key: 'year', label: '届别', pick: record => String(record.year) },
  { key: 'city', label: '地区', pick: record => record.city },
  { key: 'major', label: '专业', pick: record => record.major },
  { key: 'position', label: '岗位', pick: record => record.position },
  { key: 'degree', label: '学历', pick: record => record.degree },
  { key: 'dateYear', label: '收录年份', pick: record => record.date.slice(0, 4) },
]

export function FilterPanel({ records, filters, onChange }: { records: ExperienceRecord[]; filters: SearchFilters; onChange: (next: SearchFilters) => void }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [more, setMore] = useState(false)
  const activeCount = Object.values(filters).filter(Boolean).length
  return <aside className="filter-panel"><div className="filter-head"><div><SlidersHorizontal size={17} /><strong>筛选</strong></div>{activeCount > 0 && <button className="filter-reset" onClick={() => onChange({})}><RotateCcw size={13} /> 清除</button>}</div>
    {sections.map(section => {
      if (!more && !filters[section.key] && (section.key === 'degree' || section.key === 'dateYear')) return null
      const counts = new Map<string, number>()
      records.forEach(record => { const value = section.pick(record); if (value && value !== '0' && value !== '待核对') counts.set(value, (counts.get(value) || 0) + 1) })
      const options = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-CN'))
      const visible = expanded[section.key] ? options : options.slice(0, section.key === 'major' ? 4 : 5)
      return <section className="filter-section" key={section.key}><div className="filter-section-title"><h3>{section.label}</h3></div><div className="filter-options">
        <AnimatePresence initial={false}>{visible.map(([value, count]) => <motion.button layout initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} key={value} type="button" className={`filter-option ${filters[section.key] === value ? 'selected' : ''}`} onClick={() => onChange({ ...filters, [section.key]: filters[section.key] === value ? undefined : value })}><span className="option-radio" /><span>{value}{section.key === 'year' ? ' 届' : ''}</span><small>{count}</small></motion.button>)}</AnimatePresence>
      </div>{options.length > visible.length || expanded[section.key] ? <button className="filter-more" onClick={() => setExpanded(old => ({ ...old, [section.key]: !old[section.key] }))}>{expanded[section.key] ? '收起' : `查看全部 ${options.length} 项`} <span>{expanded[section.key] ? '−' : '+'}</span></button> : null}</section>
    })}
    <button className="filter-more filter-more-sections" onClick={() => setMore(open => !open)}>{more ? '收起更多筛选' : '更多筛选'} <span>{more ? '−' : '+'}</span></button>
  </aside>
}
