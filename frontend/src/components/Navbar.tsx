import { ArrowUpRight, Compass, Database, Search, LayoutDashboard } from 'lucide-react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { startTransition, useEffect, useState, type CSSProperties, type MouseEvent } from 'react'
import { warmPage } from '../lib/pageModules'

const items = [
  { to: '/', label: '首页', icon: LayoutDashboard, end: true },
  { to: '/search', label: '信息检索', icon: Search, end: false },
  { to: '/explore', label: '数据探索', icon: Compass, end: false },
  { to: '/workspace', label: '数据更新', icon: Database, end: false },
]

export function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const [pendingPath, setPendingPath] = useState<string | null>(null)
  useEffect(() => { setPendingPath(null) }, [location.pathname, location.search])
  const selectedPath = pendingPath ?? location.pathname
  const activeIndex = Math.max(0, items.findIndex(item => item.end ? selectedPath === item.to : selectedPath.startsWith(item.to)))

  function select(event: MouseEvent<HTMLAnchorElement>, path: string) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    setPendingPath(path)
    warmPage(path)
    startTransition(() => navigate(path))
  }
  return (
    <header className="site-nav">
      <div className="nav-drag-zone pywebview-drag-region" aria-hidden="true" />
      <NavLink to="/" className="brand" aria-label="知序首页" data-liquid>
        <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>
        <span className="brand-type"><strong>知序</strong></span>
      </NavLink>
      <nav className="nav-links" aria-label="主导航" style={{ '--nav-index': activeIndex } as CSSProperties}>
        <span className="nav-selection" aria-hidden="true" />
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} data-liquid aria-label={label}
            onClick={event => select(event, to)} onPointerEnter={() => warmPage(to)} onFocus={() => warmPage(to)}
            className={`nav-link ${items[activeIndex].to === to ? 'is-active' : ''}`}>
              <span className="nav-link-content"><Icon size={16} strokeWidth={1.8} aria-hidden="true" /><span className="nav-label">{label}</span></span>
          </NavLink>
        ))}
      </nav>
      <div className="nav-meta"><span className="status-dot" /><span>本地数据</span></div>
      <NavLink to="/search" className="nav-quick" data-liquid aria-label="打开检索"><ArrowUpRight size={18} /></NavLink>
    </header>
  )
}
