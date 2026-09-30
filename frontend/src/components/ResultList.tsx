import { Inbox, LoaderCircle } from 'lucide-react'
import type { ExperienceRecord } from '../types'
import { ResultItem } from './ResultItem'

export function ResultList({ records, loading, onOpen }: { records: ExperienceRecord[]; loading: boolean; onOpen: (record: ExperienceRecord) => void }) {
  if (loading) return <div className="result-loading"><LoaderCircle size={24} className="spin" /><span>正在检索…</span></div>
  if (!records.length) return <div className="result-empty"><Inbox size={26} /><h3>没有找到记录</h3><p>请修改关键词或筛选条件。</p></div>
  return <div className="result-list">{records.map((record, index) => <ResultItem key={record.id} record={record} index={index} onOpen={onOpen} />)}</div>
}
