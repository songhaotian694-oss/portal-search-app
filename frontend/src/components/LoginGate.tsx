import { useEffect, useState } from 'react'
import { ArrowRight, LockKeyhole, RefreshCw, Settings2 } from 'lucide-react'
import { api, type AuthStatus, type PortalSettings } from '../services/api'

export function LoginGate({ started, checkError, onAuthenticated, onRefresh }: {
  started: boolean
  checkError: string
  onAuthenticated: (status: AuthStatus) => void
  onRefresh: () => Promise<void>
}) {
  const [settings, setSettings] = useState<PortalSettings | null>(null)
  const [portalUrl, setPortalUrl] = useState('')
  const [domains, setDomains] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    void api.getSettings().then(value => {
      setSettings(value)
      setPortalUrl(value.portal_url)
      setDomains(value.allowed_domains.join(', '))
      setSettingsOpen(value.portal_url.startsWith('https://TODO'))
    }).catch(cause => setError((cause as Error).message))
  }, [])

  async function openLogin() {
    setBusy(true); setError(''); setMessage('')
    try {
      await api.openLogin()
      setMessage('请在登录窗口完成认证。登录成功后会自动进入软件。')
      await onRefresh()
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(false) }
  }

  async function confirm() {
    setBusy(true); setError('')
    try {
      const status = await api.confirmLogin()
      if (status.logged_in) onAuthenticated(status)
      else setMessage('尚未检测到登录成功，请完成门户认证后重试。')
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(false) }
  }

  async function saveSettings() {
    if (!settings) return
    setBusy(true); setError(''); setMessage('')
    try {
      const saved = await api.saveSettings({ ...settings, portal_url: portalUrl.trim(), allowed_domains: domains.split(/[,，\s]+/).filter(Boolean) })
      setSettings(saved)
      setSettingsOpen(false)
      setMessage('门户设置已保存。')
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(false) }
  }

  return <div className="login-page">
    <header className="login-brand"><span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span><strong>知序</strong></header>
    <main className="login-panel">
      <span className="login-symbol"><LockKeyhole size={22} /></span>
      <h1>请先登录</h1>
      <p>登录学校门户后，即可使用信息检索和数据整理功能。</p>
      <div className="login-actions">
        <button className="login-primary" onClick={() => void openLogin()} disabled={busy || !settings || portalUrl.startsWith('https://TODO')}>打开登录窗口 <ArrowRight size={17} /></button>
        <button className="login-secondary" onClick={() => void confirm()} disabled={busy || !started}><RefreshCw size={15} /> 检查登录状态</button>
      </div>
      {(error || checkError) && <p className="login-error" role="alert">{error || checkError}</p>}
      {message && <p className="login-message" role="status">{message}</p>}
      <div className="login-settings">
        <button className="login-settings-toggle" onClick={() => setSettingsOpen(open => !open)} aria-expanded={settingsOpen}><Settings2 size={15} /> 门户设置</button>
        {settingsOpen && <div className="login-settings-fields">
          <label>登录页地址<input type="url" value={portalUrl} onChange={event => setPortalUrl(event.target.value)} placeholder="https://..." /></label>
          <label>允许域名<input value={domains} onChange={event => setDomains(event.target.value)} placeholder="例如：example.edu.cn" /></label>
          <button onClick={() => void saveSettings()} disabled={busy || !settings || !portalUrl.startsWith('https://')}>保存设置</button>
        </div>}
      </div>
    </main>
  </div>
}
