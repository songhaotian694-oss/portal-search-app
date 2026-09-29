import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUpRight, BookOpenText, FileText, MapPin, X } from 'lucide-react'
import type { ExperienceRecord } from '../types'

export function DetailDrawer({ record, onClose }: { record: ExperienceRecord | null; onClose: () => void }) {
  useEffect(() => {
    if (!record) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const key = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', key)
    return () => { document.body.style.overflow = previous; window.removeEventListener('keydown', key) }
  }, [record, onClose])
  return <AnimatePresence>{record && <div className="drawer-root"><motion.button aria-label="关闭详情" className="drawer-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} /><motion.aside className="detail-drawer" role="dialog" aria-modal="true" aria-label="记录详情" initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }}>
    <div className="drawer-head"><div><span className="eyebrow">RECORD / {record.id}</span><h2>线索详情</h2></div><button aria-label="关闭详情" onClick={onClose}><X size={21} /></button></div>
    <div className="drawer-profile"><span className="drawer-avatar">{record.person.slice(-2)}</span><div><small>本地提取记录 · {record.needsReview ? '待人工核对' : '字段较完整'}</small><h3>{record.person}</h3><span>{record.year ? `${record.year} 届` : '届别待核对'} · {record.degree}</span></div></div>
    <div className="drawer-facts"><div><small>专业方向</small><strong>{record.major}</strong></div><div><small>地区</small><strong><MapPin size={15} />{record.city}</strong></div><div><small>岗位</small><strong>{record.position}</strong></div><div><small>单位类型</small><strong>{record.organization}</strong></div></div>
    <section className="drawer-section"><div className="drawer-section-title"><BookOpenText size={18} /><h4>提取证据</h4></div><p>{record.detail}</p></section>
    <section className="drawer-section"><div className="drawer-section-title"><FileText size={18} /><h4>数据来源</h4></div><div className="source-box"><strong>{record.source}</strong>{record.sourceUrl && /^https?:\/\//i.test(record.sourceUrl) && <a href={record.sourceUrl} target="_blank" rel="noreferrer">打开来源文章 <ArrowUpRight size={14} /></a>}<small>发布日期 · {record.date || '未标注'}</small></div></section>
    <div className="drawer-bottom"><div><span>提取状态</span><strong>{record.needsReview ? '待人工核对' : '字段较完整'}</strong></div><button onClick={onClose}>返回结果列表 <ArrowUpRight size={17} /></button></div>
  </motion.aside></div>}</AnimatePresence>
}
