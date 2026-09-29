import { useEffect, useState } from 'react'
import { ArrowUpRight, Boxes, CircleDot } from 'lucide-react'
import { DataExplorer } from '../components/DataExplorer'
import { api } from '../services/api'
import type { ExperienceRecord } from '../types'

export function ExplorePage({ onSearch }: { onSearch: (query: string) => void }) {
  const [records, setRecords] = useState<ExperienceRecord[]>([])
  useEffect(() => { void api.getRecords().then(setRecords) }, [])
  return <div className="explore-page"><div className="explore-heading"><div><span className="eyebrow">03 / DATA EXPLORATION</span><h1>看见信息之间的连接<span>。</span></h1><p>选取不同维度，观察专业、地区与岗位如何形成新的路径。</p></div><div className="explore-heading-mark"><Boxes size={22} /><span>INTERACTIVE<br />DATA FIELD</span><ArrowUpRight size={17} /></div></div><div className="explore-meta"><span><CircleDot size={13} /> 当前载入 {records.length} 条演示记录</span><span>拖动页面不会改变图表选择 · 点击节点继续探索</span></div><DataExplorer records={records} onSearch={onSearch} /></div>
}
