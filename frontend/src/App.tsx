import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { LoginGate } from './components/LoginGate'
import { useLiquidFeedback } from './hooks/useLiquidFeedback'
import { api, type AuthStatus } from './services/api'
import type { Facet } from './types'

const HomePage = lazy(() => import('./pages/HomePage').then(module => ({ default: module.HomePage })))
const SearchPage = lazy(() => import('./pages/SearchPage').then(module => ({ default: module.SearchPage })))
const ExplorePage = lazy(() => import('./pages/ExplorePage').then(module => ({ default: module.ExplorePage })))
const WorkspacePage = lazy(() => import('./pages/WorkspacePage').then(module => ({ default: module.WorkspacePage })))

export default function App() {
  useLiquidFeedback()
  const navigate = useNavigate()
  const location = useLocation()
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [checked, setChecked] = useState(false)
  const [authError, setAuthError] = useState('')
  const refreshAuth = useCallback(async () => {
    try { setAuth(await api.authStatus()); setAuthError('') }
    catch (cause) { setAuthError((cause as Error).message) }
    finally { setChecked(true) }
  }, [])
  useEffect(() => {
    void refreshAuth()
    const timer = window.setInterval(() => { void refreshAuth() }, 5000)
    return () => window.clearInterval(timer)
  }, [refreshAuth])
  const search = useCallback((query: string, priority: Facet[] = []) => {
    if (!query.trim()) return
    navigate(`/search?q=${encodeURIComponent(query.trim())}&priority=${priority.join(',')}`)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [navigate])
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }) }, [location.pathname])
  if (!checked) return <div className="route-loading">正在检查登录状态…</div>
  if (!auth?.logged_in) return <LoginGate started={Boolean(auth?.started)} checkError={authError} onAuthenticated={setAuth} onRefresh={refreshAuth} />
  return <Layout><Suspense fallback={<div className="route-loading">加载中…</div>}><Routes><Route path="/" element={<HomePage onSearch={search} />} /><Route path="/search" element={<SearchPage onSearch={search} />} /><Route path="/explore" element={<ExplorePage onSearch={search} />} /><Route path="/workspace" element={<WorkspacePage />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></Suspense></Layout>
}
