import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { RotateCcw, SlidersHorizontal } from 'lucide-react'
import type { ExperienceRecord, SearchFilters } from '../types'

type FilterKey = keyof SearchFilters
const sections: { key: FilterKey; label: string; pick: (record: ExperienceRecord) => string }[] = [
  { key: 'year', label: '届别', pick: record => String(record.year) },
  { key: 'dateYear', label: '收录年份', pick: record => record.date.slice(0, 4) },
  { key: 'city', label: '地区', pick: record => record.city },
  { key: 'major', label: '专业', pick: record => record.major },
  { key: 'position', label: '岗位', pick: record => record.position },
  { key: 'degree', label: '学历', pick: record => record.degree },
]

export function FilterPanel({ records, filters, onChange }: { records: ExperienceRecord[]; filters: SearchFilters; onChange: (next: SearchFilters) => void }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const activeCount = Object.values(filters).filter(Boolean).length
  return <aside className="filter-panel"><div className="filter-head"><div><SlidersHorizontal size={17} /><strong>动态筛选</strong></div><small>{String(activeCount).padStart(2, '0')} ACTIVE</small></div><button className="filter-reset" onClick={() => onChange({})}><RotateCcw size={13} /> 清除全部</button>
    {sections.map(section => {
      const counts = new Map<string, number>()
      records.forEach(record => { const value = section.pick(record); if (value && value !== '0' && value !== '待核对') counts.set(value, (counts.get(value) || 0) + 1) })
      const options = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-CN'))
      const visible = expanded[section.key] ? options : options.slice(0, section.key === 'major' ? 4 : 5)
      return <section className="filter-section" key={section.key}><div className="filter-section-title"><h3>{section.label}</h3><span>{String(options.length).padStart(2, '0')}</span></div><div className="filter-options">
        <AnimatePresence initial={false}>{visible.map(([value, count]) => <motion.button layout initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} key={value} type="button" className={`filter-option ${filters[section.key] === value ? 'selected' : ''}`} onClick={() => onChange({ ...filters, [section.key]: filters[section.key] === value ? undefined : value })}><span className="option-radio" /><span>{value}{section.key === 'year' ? ' 届' : ''}</span><small>{count}</small></motion.button>)}</AnimatePresence>
      </div>{options.length > visible.length || expanded[section.key] ? <button className="filter-more" onClick={() => setExpanded(old => ({ ...old, [section.key]: !old[section.key] }))}>{expanded[section.key] ? '收起' : `查看全部 ${options.length} 项`} <span>{expanded[section.key] ? '−' : '+'}</span></button> : null}</section>
    })}
    <div className="filter-foot"><span className="status-dot" /> 修改条件后结果实时更新</div>
  </aside>
}
