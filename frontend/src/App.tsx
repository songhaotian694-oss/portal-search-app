import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { LoginGate } from './components/LoginGate'
import { useLiquidFeedback } from './hooks/useLiquidFeedback'
import { api, type AuthStatus } from './services/api'
import type { Facet } from './types'
import { pageModules, warmPagesWhenIdle } from './lib/pageModules'

const HomePage = lazy(pageModules['/'])
const SearchPage = lazy(pageModules['/search'])
const ExplorePage = lazy(pageModules['/explore'])
const WorkspacePage = lazy(pageModules['/workspace'])

export default function App() {
  useLiquidFeedback()
  const navigate = useNavigate()
  const location = useLocation()
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [checked, setChecked] = useState(false)
  const [authError, setAuthError] = useState('')
  const wasLoggedIn = useRef(false)
  const [dataMessage, setDataMessage] = useState('')
  const [dataVersion, setDataVersion] = useState(0)
  useEffect(() => {
    if (!auth?.logged_in) return
    let cancelled = false
    let timer = 0
    const monitor = async () => {
      try {
        const [sync, process] = await Promise.all([api.syncStatus(), api.processStatus()])
        if (cancelled) return
        if (sync.status === 'failed' || process.status === 'failed') { setDataMessage(sync.status === 'failed' ? sync.message : process.message); return }
        if (sync.status === 'running' || process.status === 'running') {
          setDataMessage(process.status === 'running' ? `正在自动识别与整理 ${process.current}/${process.total || '—'}` : `正在首次获取学校资料 ${sync.current}/${sync.total || '—'}`)
          timer = window.setTimeout(() => { void monitor() }, 2500)
        } else { setDataMessage(''); setDataVersion(value => value + 1) }
      } catch (cause) { if (!cancelled) setDataMessage((cause as Error).message) }
    }
    void api.ensureData().then(result => { if (!cancelled && result.started) { setDataMessage('正在准备自动整理资料…'); void monitor() } }).catch(cause => { if (!cancelled) setDataMessage((cause as Error).message) })
    return () => { cancelled = true; window.clearTimeout(timer) }
  }, [auth?.logged_in])
  useEffect(() => {
    if (auth?.logged_in) return warmPagesWhenIdle()
  }, [auth?.logged_in])
  const refreshAuth = useCallback(async () => {
    try { setAuth(await api.authStatus()); setAuthError('') }
    catch (cause) { setAuthError((cause as Error).message) }
    finally { setChecked(true) }
  }, [])
  useEffect(() => {
    void refreshAuth()
  }, [refreshAuth])
  useEffect(() => {
    const timer = window.setInterval(() => { void refreshAuth() }, auth?.login_open ? 1500 : 5000)
    return () => window.clearInterval(timer)
  }, [refreshAuth, auth?.login_open])
  useEffect(() => {
    const loggedIn = Boolean(auth?.logged_in)
    if (loggedIn && !wasLoggedIn.current) navigate('/', { replace: true })
    wasLoggedIn.current = loggedIn
  }, [auth?.logged_in, navigate])
  const search = useCallback((query: string, priority: Facet[] = []) => {
    if (!query.trim()) return
    navigate(`/search?q=${encodeURIComponent(query.trim())}&priority=${priority.join(',')}`)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [navigate])
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }) }, [location.pathname])
  if (!checked) return <div className="route-loading">正在检查登录状态…</div>
  if (!auth?.logged_in) return <LoginGate status={auth} checkError={authError} onStatusChange={status => setAuth(current => ({ ...current, ...status }))} onRememberChanged={rememberLogin => setAuth(current => current ? { ...current, remember_login: rememberLogin } : current)} onRefresh={refreshAuth} />
  return <Layout>{dataMessage && <div className="auto-data-status" role="status"><span>{dataMessage}</span><Link to="/workspace">查看进度</Link></div>}<Suspense fallback={<div className="route-loading">加载中…</div>}><Routes key={dataVersion}><Route path="/" element={<HomePage onSearch={search} />} /><Route path="/search" element={<SearchPage onSearch={search} />} /><Route path="/explore" element={<ExplorePage onSearch={search} />} /><Route path="/workspace" element={<WorkspacePage />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></Suspense></Layout>
}
