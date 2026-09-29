import { useEffect, useState } from 'react'
import { DataExplorer } from '../components/DataExplorer'
import { api } from '../services/api'
import type { ExperienceRecord } from '../types'

export function ExplorePage({ onSearch }: { onSearch: (query: string) => void }) {
  const [records, setRecords] = useState<ExperienceRecord[]>([])
  const [error, setError] = useState('')
  useEffect(() => { void api.getRecords().then(setRecords).catch(cause => setError((cause as Error).message)) }, [])
  return <div className="explore-page"><div className="explore-heading"><div><h1>数据探索</h1></div></div><div className="explore-meta"><span>{records.length} 条记录</span></div>{error ? <p className="workspace-message">{error}</p> : records.length ? <DataExplorer records={records} onSearch={onSearch} /> : <p className="workspace-message">暂无记录，请先到“数据更新”获取资料。</p>}</div>
}
