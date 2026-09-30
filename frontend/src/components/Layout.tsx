import { motion, useReducedMotion } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Navbar } from './Navbar'

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const reducedMotion = useReducedMotion()
  return (
    <div className="app-shell">
      <Navbar />
        <motion.main
          key={location.pathname}
          className="page-content"
          initial={{ opacity: reducedMotion ? 1 : 0.94 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reducedMotion ? 0 : 0.18, ease: 'easeOut' }}
        >
          {children}
        </motion.main>
      <footer className="site-footer"><span>知序 © 2026</span><span>数据保存在本机</span></footer>
    </div>
  )
}
