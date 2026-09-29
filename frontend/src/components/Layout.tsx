import { AnimatePresence, motion } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Navbar } from './Navbar'

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  return (
    <div className="app-shell">
      <Navbar />
      <AnimatePresence mode="wait" initial={false}>
        <motion.main key={location.pathname} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}>
          {children}
        </motion.main>
      </AnimatePresence>
      <footer className="site-footer"><span>知序 © 2026</span><span>数据保存在本机</span></footer>
    </div>
  )
}
