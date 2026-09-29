import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { QueryParser } from './components/QueryParser'
import type { Facet } from './types'

const HomePage = lazy(() => import('./pages/HomePage').then(module => ({ default: module.HomePage })))
const SearchPage = lazy(() => import('./pages/SearchPage').then(module => ({ default: module.SearchPage })))
const ExplorePage = lazy(() => import('./pages/ExplorePage').then(module => ({ default: module.ExplorePage })))
const WorkspacePage = lazy(() => import('./pages/WorkspacePage').then(module => ({ default: module.WorkspacePage })))

export default function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const [pending, setPending] = useState<{ query: string; priority: Facet[] } | null>(null)
  const search = useCallback((query: string, priority: Facet[] = []) => { if (query.trim()) setPending({ query: query.trim(), priority }) }, [])
  const complete = useCallback(() => {
    if (!pending) return
    navigate(`/search?q=${encodeURIComponent(pending.query)}&priority=${pending.priority.join(',')}`)
    setPending(null)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [navigate, pending])
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }) }, [location.pathname])
  return <><Layout><Suspense fallback={<div className="route-loading">正在整理界面…</div>}><Routes><Route path="/" element={<HomePage onSearch={search} />} /><Route path="/search" element={<SearchPage onSearch={search} />} /><Route path="/explore" element={<ExplorePage onSearch={search} />} /><Route path="/workspace" element={<WorkspacePage />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></Suspense></Layout><QueryParser query={pending?.query ?? null} onComplete={complete} /></>
}
