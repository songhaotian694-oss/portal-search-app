import { useEffect, useState } from 'react'
import { ArrowRight, LockKeyhole, RefreshCw, Settings2 } from 'lucide-react'
import { api, type AuthStatus, type PortalSettings } from '../services/api'

export function LoginGate({ status, checkError, onStatusChange, onRememberChanged, onRefresh }: {
  status: AuthStatus | null
  checkError: string
  onStatusChange: (status: AuthStatus) => void
  onRememberChanged: (rememberLogin: boolean) => void
  onRefresh: () => Promise<void>
}) {
  const [settings, setSettings] = useState<PortalSettings | null>(null)
  const [portalUrl, setPortalUrl] = useState('')
  const [domains, setDomains] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [savingPreference, setSavingPreference] = useState(false)
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
      const next = await api.openLogin(Boolean(status?.remember_login))
      onStatusChange(next)
      setMessage(next.logged_in ? '' : next.embedded ? '请在软件内完成学校认证。登录成功后会自动进入首页并关闭登录页面。' : '请在登录浏览器中完成学校认证。登录成功后会自动进入首页并关闭登录窗口。')
      await onRefresh()
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(false) }
  }

  async function confirm() {
    setBusy(true); setError('')
    try {
      const status = await api.confirmLogin()
      onStatusChange(status)
      if (!status.logged_in) setMessage(status.message || '尚未检测到登录成功，请完成学校认证后重试。')
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(false) }
  }

  async function changeRemember(rememberLogin: boolean) {
    setSavingPreference(true); setError(''); setMessage('')
    try {
      const saved = await api.saveAuthPreferences(rememberLogin)
      onRememberChanged(saved.remember_login)
      setMessage(saved.remember_login ? '登录状态将保留在本机，下次打开软件会自动检查并进入首页。' : '已关闭保留登录状态，下次打开软件需要重新登录。')
    } catch (cause) { setError((cause as Error).message) }
    finally { setSavingPreference(false) }
  }

  async function cancelLogin() {
    setBusy(true); setError(''); setMessage('')
    try {
      onStatusChange(await api.cancelLogin())
      setMessage('已关闭登录页面，可随时重新开始。')
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
    <header className="login-brand pywebview-drag-region"><span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span><strong>知序</strong></header>
    <div className="login-center">
    <main className="login-panel">
      <span className="login-symbol"><LockKeyhole size={22} /></span>
      <h1>请先登录</h1>
      <label className="login-remember">
        <input type="checkbox" checked={Boolean(status?.remember_login)} disabled={busy || savingPreference || !status} onChange={event => void changeRemember(event.target.checked)} />
        <span><strong>在本机保留登录状态</strong></span>
      </label>
      <div className="login-actions">
        <button className="login-primary" data-liquid onClick={() => void openLogin()} disabled={busy || savingPreference || !settings || portalUrl.startsWith('https://TODO')}>{status?.login_open ? '返回登录页面' : status?.embedded ? '在软件内登录' : '打开登录窗口'} <ArrowRight size={17} /></button>
        <button className="login-secondary" data-liquid onClick={() => void confirm()} disabled={busy || savingPreference || !status?.started}><RefreshCw size={15} /> 检查登录状态</button>
        {status?.login_open && <button className="login-cancel" onClick={() => void cancelLogin()} disabled={busy}>取消登录</button>}
      </div>
      {(error || checkError) && <p className="login-error" role="alert">{error || checkError}</p>}
      {(message || status?.message) && <p className={`login-message ${/过期|无法|尚未|未能/.test(message || status?.message || '') ? 'login-message-warning' : ''}`} role="status">{message || status?.message}</p>}
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
  </div>
}
