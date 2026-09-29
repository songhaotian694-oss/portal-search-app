import { AnimatePresence } from 'framer-motion'
import { Inbox, LoaderCircle } from 'lucide-react'
import type { ExperienceRecord } from '../types'
import { ResultItem } from './ResultItem'

export function ResultList({ records, loading, onOpen }: { records: ExperienceRecord[]; loading: boolean; onOpen: (record: ExperienceRecord) => void }) {
  if (loading) return <div className="result-loading"><LoaderCircle size={24} className="spin" /><span>正在重排线索…</span></div>
  if (!records.length) return <div className="result-empty"><Inbox size={26} /><h3>当前条件下没有记录</h3><p>调整左侧筛选项，或尝试更宽泛的自然语言提问。</p></div>
  return <div className="result-list"><AnimatePresence initial={false}>{records.map((record, index) => <ResultItem key={record.id} record={record} index={index} onOpen={onOpen} />)}</AnimatePresence></div>
}
