import { useCallback, useEffect, useState } from 'react'
import { ArrowDownToLine, Database, LockKeyhole, RefreshCw, Settings2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, type AuthStatus, type JobStatus, type PortalSettings } from '../services/api'
import type { Overview } from '../types'

const blank: JobStatus = { status: 'idle', current: 0, total: 0, message: '' }
const emptyOverview: Overview = { records: 0, cities: 0, majors: 0, latestYear: 0, articles: 0, needsReview: 0, lastSync: null }
const label: Record<string, string> = { idle: '待启动', running: '正在后台运行', completed: '已完成', failed: '需要处理' }

export function WorkspacePage() {
  const [auth, setAuth] = useState<AuthStatus>({ logged_in: false, url: '' })
  const [sync, setSync] = useState<JobStatus>(blank)
  const [process, setProcess] = useState<JobStatus>(blank)
  const [overview, setOverview] = useState<Overview>(emptyOverview)
  const [settings, setSettings] = useState<PortalSettings | null>(null)
  const [domains, setDomains] = useState('')
  const [keywords, setKeywords] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [nextAuth, nextSync, nextProcess, nextOverview] = await Promise.all([api.authStatus(), api.syncStatus(), api.processStatus(), api.getOverview()])
      setAuth(nextAuth); setSync(nextSync); setProcess(nextProcess); setOverview(nextOverview)
    } catch (error) { setMessage((error as Error).message) }
  }, [])
  useEffect(() => {
    void refresh()
    void api.getSettings().then(value => { setSettings(value); setDomains(value.allowed_domains.join(', ')); setKeywords(value.api_keywords.join(', ')) }).catch(error => setMessage((error as Error).message))
    const timer = window.setInterval(() => { void refresh() }, 2500)
    return () => window.clearInterval(timer)
  }, [refresh])

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true); setMessage('')
    try { await action(); setMessage(success); await refresh() }
    catch (error) { setMessage((error as Error).message) }
    finally { setBusy(false) }
  }
  async function save() {
    if (!settings) return
    await run(async () => {
      const values = { ...settings, allowed_domains: domains.split(/[,，\s]+/).map(x => x.trim()).filter(Boolean), api_keywords: keywords.split(/[,，]+/).map(x => x.trim()).filter(Boolean) }
      setSettings(await api.saveSettings(values))
    }, '门户设置已保存在本机。')
  }

  return <div className="workspace-page">
    <div className="workspace-heading"><div><h1>数据更新</h1></div><button className="workspace-refresh" onClick={() => void refresh()}><RefreshCw size={16} /> 刷新状态</button></div>
    {message && <p className="workspace-message" role="status">{message}</p>}
    <div className="workspace-stats"><div><small>有效记录</small><strong>{overview.records}</strong><Link to="/search">进入检索 →</Link></div><div><small>来源文章</small><strong>{overview.articles}</strong></div><div><small>待核对</small><strong>{overview.needsReview}</strong></div><div><small>最近同步</small><strong className="workspace-date">{overview.lastSync?.slice(0, 10) || '尚未同步'}</strong></div></div>
    <div className="workspace-grid"><section className="workspace-section"><div className="workspace-section-head"><LockKeyhole size={19} /><div><h2>门户登录</h2></div><span className={`workspace-pill ${auth.logged_in ? 'good' : ''}`}>{auth.logged_in ? '已登录' : '未确认登录'}</span></div><div className="workspace-actions"><button disabled={busy} onClick={() => void run(api.openLogin, '登录窗口已打开，请在其中完成认证。')}>打开登录窗口</button><button disabled={busy} onClick={() => void run(api.confirmLogin, '已检查登录状态。')}>确认登录</button></div></section>
      <section className="workspace-section"><div className="workspace-section-head"><Database size={19} /><div><h2>获取与处理</h2></div><span className={`workspace-pill ${sync.status === 'completed' ? 'good' : ''}`}>{label[sync.status] || sync.status}</span></div><div className="workspace-actions"><button disabled={busy || sync.status === 'running'} onClick={() => void run(() => api.startSync('full'), '数据更新已启动。')}>更新数据</button><button disabled={busy || sync.status === 'running'} onClick={() => void run(() => api.startSync('test'), '测试获取已启动。')}>测试连接</button></div>{sync.status !== 'idle' && <div className="workspace-progress"><span>同步 {sync.current}/{sync.total || '—'} · 成功 {sync.success || 0} · 失败 {sync.failed || 0}</span><progress value={sync.current} max={Math.max(sync.total, 1)} />{sync.message && <small>{sync.message}</small>}</div>}{process.status !== 'idle' && <div className="workspace-progress"><span>识别 {process.current}/{process.total || '—'} · {label[process.status] || process.status}</span><progress value={process.current} max={Math.max(process.total, 1)} />{process.message && <small>{process.message}</small>}</div>}<div className="workspace-actions secondary"><button disabled={busy || sync.status === 'running'} onClick={() => void run(api.retrySync, '失败任务重试已启动。')}>重试失败项</button><button disabled={busy || process.status === 'running'} onClick={() => void run(() => api.startProcess(true), '重新识别已启动。')}>重新识别</button></div></section></div>
    <div className="workspace-bottom"><section className="workspace-section"><div className="workspace-section-head"><ArrowDownToLine size={19} /><div><h2>导出资料</h2></div></div><a className="workspace-download" href="/api/export">导出 Excel <ArrowDownToLine size={15} /></a></section><section className="workspace-section"><div className="workspace-section-head"><Settings2 size={19} /><div><h2>门户设置</h2></div></div><button className="workspace-toggle" onClick={() => setShowSettings(open => !open)}>{showSettings ? '收起设置' : '编辑设置'}</button>{showSettings && settings && <div className="workspace-form"><label>登录页地址<input value={settings.portal_url} onChange={event => setSettings({ ...settings, portal_url: event.target.value })} /></label><label>就业栏目地址<input value={settings.employment_entry} onChange={event => setSettings({ ...settings, employment_entry: event.target.value })} /></label><label>允许域名（逗号分隔）<input value={domains} onChange={event => setDomains(event.target.value)} /></label><label>检索关键词（逗号分隔）<input value={keywords} onChange={event => setKeywords(event.target.value)} /></label><label>获取方式<select value={settings.data_source} onChange={event => setSettings({ ...settings, data_source: event.target.value })}><option value="api">门户接口</option><option value="auto">自动</option><option value="page">网页</option></select></label><button disabled={busy} onClick={() => void save()}>保存到本机</button></div>}</section></div>
  </div>
}
