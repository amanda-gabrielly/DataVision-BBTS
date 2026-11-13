import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, getToken, setToken } from './api'
import { AppCtx, go, useRoute } from './app-context'
import { Ic } from './icons'
import { iniciais } from './util'
import DocDrawer from './components/DocDrawer'
import UploadModal from './components/UploadModal'
import Painel from './pages/Painel'
import Perguntar from './pages/Perguntar'
import Documentos from './pages/Documentos'
import Relatorios from './pages/Relatorios'
import Salvos from './pages/Salvos'
import Perfil from './pages/Perfil'
import Login from './pages/Login'

const NAV = [
  ['painel', 'Painel', 'home'], ['perguntar', 'Perguntar à IA', 'chat'], ['documentos', 'Documentos', 'folder'],
  ['relatorios', 'Relatórios', 'chart'], ['salvos', 'Salvos', 'flag'],
]

function applyTheme(t) {
  if (t === 'dark' || t === 'light') document.documentElement.dataset.theme = t
  else delete document.documentElement.dataset.theme
}

function Shell({ me, setMe, onLogout }) {
  const route = useRoute()
  const page = route.parts[0] || 'painel'
  const routeKey = route.parts.join('/') + '?' + route.q.toString()
  const [toastMsg, setToast] = useState(null)
  const [drawer, setDrawer] = useState(null) // { id, pagina?, versao? }
  const [upload, setUpload] = useState(false)
  const [tick, setTick] = useState(0) // força recarregar listas após upload/salvar
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem('dv-theme') || '' } catch { return '' } })
  const [salvosN, setSalvosN] = useState(0)
  const [pastas, setPastas] = useState([])

  useEffect(() => { applyTheme(theme); try { localStorage.setItem('dv-theme', theme) } catch { /* sem storage */ } }, [theme])
  useEffect(() => { api.pastas().then(setPastas).catch(() => {}) }, [tick])
  useEffect(() => { api.documentos({ salvos: 1 }).then((d) => setSalvosN(d.length)).catch(() => {}) }, [tick])

  const toast = useCallback((m) => { setToast(m); setTimeout(() => setToast(null), 2800) }, [])
  const refresh = useCallback(() => setTick((t) => t + 1), [])
  const toggleSalvo = useCallback(async (doc) => {
    try {
      if (doc.salvo) { await api.removerSalvo(doc.id); toast('Removido dos salvos') }
      else { await api.salvar(doc.id); toast('Documento salvo') }
      refresh()
    } catch (e) { toast(e.message) }
  }, [refresh, toast])

  const ctx = useMemo(() => ({
    me, setMe, toast, tick, refresh, toggleSalvo, theme, setTheme,
    openDoc: (id, extra = {}) => setDrawer({ id, routeKey, ...extra }), openUpload: () => setUpload(true),
  }), [me, setMe, toast, tick, refresh, toggleSalvo, theme, routeKey])

  const view = {
    painel: <Painel />, perguntar: <Perguntar route={route} />, documentos: <Documentos route={route} />,
    relatorios: <Relatorios route={route} />, salvos: <Salvos />, perfil: <Perfil />,
  }[page] || <Painel />

  return (
    <AppCtx.Provider value={ctx}>
      <div className="app">
        <aside className="side">
          <a className="brandlogo" href="#/painel" aria-label="BBTS Data Vision — início"><img src="/logo.png" alt="BBTS Data Vision" /></a>
          {NAV.map(([k, label, ic]) => (
            <a key={k} className={'nv' + (page === k ? ' on' : '')} href={`#/${k}`}>
              <Ic n={ic} />{label}{k === 'salvos' && salvosN > 0 && <span className="cnt">{salvosN}</span>}
            </a>
          ))}
          <div className="sdiv">Pastas</div>
          {pastas.map((p) => (
            <a key={p.slug} className={'nv sm' + (route.parts[0] === 'documentos' && route.q.get('pasta') === p.slug ? ' on' : '')} href={`#/documentos?pasta=${p.slug}`}>
              <span className="dot" style={{ background: p.cor }} />{p.nome}<span className="cnt2">{p.documentos}</span>
            </a>))}
          <div className="sp" />
          <a className="me" href="#/perfil">
            <span className="av">{me?.foto ? <img src={me.foto} alt="" /> : iniciais(me?.nome)}</span>
            <span><b>{me?.nome || '…'}</b><small>{me?.perfil?.nome || me?.cargo || 'Meu perfil'}</small></span>
          </a>
          <button className="nv out" onClick={onLogout}><Ic n="x" />Sair</button>
        </aside>
        <div className="main">
          <header className="top">
            <form className="gs" role="search" onSubmit={(e) => { e.preventDefault(); const q = new FormData(e.target).get('q').trim(); if (q) go(`documentos?q=${encodeURIComponent(q)}`) }}>
              <Ic n="search" /><input name="q" placeholder="Buscar documento, código ou tipo…" aria-label="Buscar documentos" />
            </form>
            <div className="tools">
              <button className="iconbtn" title="Alternar tema" aria-label="Alternar tema"
                onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}><Ic n={theme === 'dark' ? 'sun' : 'moon'} /></button>
              <button className="btn y" onClick={() => setUpload(true)}><Ic n="upload" s={18} /><span className="lbl">Enviar documento</span></button>
            </div>
          </header>
          <main className="content">{view}</main>
        </div>
        <nav className="bnav" aria-label="Navegação">
          {NAV.map(([k, label, ic]) => <a key={k} href={`#/${k}`} className={page === k ? 'on' : ''}><Ic n={ic} />{label.split(' ')[0]}</a>)}
          <a href="#/perfil" className={page === 'perfil' ? 'on' : ''}><Ic n="user" />Perfil</a>
        </nav>
      </div>
      {drawer && drawer.routeKey === routeKey && <DocDrawer {...drawer} onClose={() => setDrawer(null)} />}
      {upload && <UploadModal onClose={() => { setUpload(false); refresh() }} />}
      {toastMsg && <div className="toast" role="status">{toastMsg}</div>}
    </AppCtx.Provider>
  )
}

export default function App() {
  const [me, setMe] = useState(null)
  const [estado, setEstado] = useState(getToken() ? 'checando' : 'login') // checando | login | ok

  useEffect(() => {
    if (!getToken()) return
    api.me().then((u) => { setMe(u); setEstado('ok') }).catch(() => { setToken(''); setEstado('login') })
  }, [])
  useEffect(() => {
    const sair = () => { setMe(null); setEstado('login') }
    window.addEventListener('dv-logout', sair)
    return () => window.removeEventListener('dv-logout', sair)
  }, [])

  const sair = useCallback(async () => {
    try { await api.logout() } catch { /* sessão já encerrada */ }
    setToken(''); setMe(null); setEstado('login'); window.location.hash = '#/painel'
  }, [])

  if (estado === 'login') return <Login onLogin={(u) => { setMe(u); setEstado('ok') }} />
  if (estado === 'checando' || !me) return <div className="skel" style={{ height: '100vh' }} />
  return <Shell key={me.id} me={me} setMe={setMe} onLogout={sair} />
}
