import { ArrowUpRight, Compass, Database, Search, Sparkles } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const items = [
  { to: '/', label: '概览', icon: Sparkles, end: true },
  { to: '/search', label: '智能检索', icon: Search, end: false },
  { to: '/explore', label: '数据探索', icon: Compass, end: false },
  { to: '/workspace', label: '数据更新', icon: Database, end: false },
]

export function Navbar() {
  return (
    <header className="site-nav">
      <NavLink to="/" className="brand" aria-label="知序首页">
        <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>
        <span className="brand-type"><strong>知序</strong><small>ZHIXU / INTELLIGENCE</small></span>
      </NavLink>
      <nav className="nav-links" aria-label="主导航">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`}>
            <Icon size={16} strokeWidth={1.8} /><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="nav-meta"><span className="status-dot" /><span>本地数据</span><Database size={14} /></div>
      <NavLink to="/search" className="nav-quick" aria-label="打开检索"><ArrowUpRight size={18} /></NavLink>
    </header>
  )
}
