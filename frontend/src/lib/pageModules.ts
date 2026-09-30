const loaders = {
  '/': () => import('../pages/HomePage').then(module => ({ default: module.HomePage })),
  '/search': () => import('../pages/SearchPage').then(module => ({ default: module.SearchPage })),
  '/explore': () => import('../pages/ExplorePage').then(module => ({ default: module.ExplorePage })),
  '/workspace': () => import('../pages/WorkspacePage').then(module => ({ default: module.WorkspacePage })),
}

export function warmPage(path: string) {
  const loader = loaders[path as keyof typeof loaders]
  if (loader) void loader().catch(() => {})
}

export const pageModules = loaders

export function warmPagesWhenIdle() {
  const paths = Object.keys(loaders)
  let cancelled = false
  let timer = 0
  let idle = 0
  const next = () => {
    if (cancelled || !paths.length) return
    const path = paths.shift()!
    void loaders[path as keyof typeof loaders]().catch(() => {}).finally(schedule)
  }
  const schedule = () => {
    if (cancelled || !paths.length) return
    if (typeof window.requestIdleCallback === 'function') idle = window.requestIdleCallback(next, { timeout: 1800 })
    else timer = window.setTimeout(next, 300)
  }
  schedule()
  return () => {
    cancelled = true
    window.clearTimeout(timer)
    if (idle) window.cancelIdleCallback(idle)
  }
}
