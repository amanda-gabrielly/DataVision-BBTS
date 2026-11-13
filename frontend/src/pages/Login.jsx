import { useEffect, useState } from 'react'
import { api, setToken } from '../api'
import { Ic } from '../icons'

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [busy, setBusy] = useState(false)
  const [demo, setDemo] = useState(null)

  useEffect(() => { api.contasDemo().then(setDemo).catch(() => {}) }, [])

  async function entrar(e) {
    e.preventDefault()
    setErro(''); setBusy(true)
    try {
      const r = await api.login(email, senha)
      setToken(r.token)
      onLogin(r.usuario)
    } catch (x) { setErro(x.message) }
    setBusy(false)
  }

  return (
    <div className="lg">
      <main className="lgc">
        <h1>Entrar</h1>
        <p className="mut">Use o e-mail e a senha da sua conta.</p>
        <form onSubmit={entrar}>
          <label className="f" htmlFor="lg-email">E-mail</label>
          <input id="lg-email" className="inp" type="email" autoComplete="username" value={email}
            onChange={(e) => setEmail(e.target.value)} required autoFocus />
          <label className="f" htmlFor="lg-senha">Senha</label>
          <input id="lg-senha" className="inp" type="password" autoComplete="current-password" value={senha}
            onChange={(e) => setSenha(e.target.value)} required />
          {erro && <div className="alert bad" role="alert"><Ic n="alert" s={18} /><span>{erro}</span></div>}
          <button className="btn y" type="submit" disabled={busy}>{busy ? 'Entrando…' : 'Entrar'}</button>
        </form>
        {demo && (
          <section className="lgd" aria-label="Contas de demonstração">
            <div className="lgd-h"><b>Contas de demonstração</b><small>senha: {demo.senha_demo}</small></div>
            <div className="lgd-g">
              {demo.contas.map((c) => (
                <button key={c.email} type="button" className={'lgd-p' + (email === c.email ? ' on' : '')} aria-pressed={email === c.email}
                  onClick={() => { setEmail(c.email); setSenha(demo.senha_demo); setErro('') }}>
                  <span className="lgd-av">{c.nome.split(' ').map((w) => w[0]).slice(0, 2).join('')}</span>
                  <b>{c.nome.split(' ')[0]}</b>
                  <small>{c.perfil_nome.split(" ")[0].replace("Administrador","Admin")}</small>
                </button>))}
            </div>
            <p className="lgd-d">{(() => { const c = demo.contas.find((x) => x.email === email); return c ? `${c.perfil_nome}: ${c.descricao}.` : 'Toque em uma pessoa para preencher o acesso.' })()}</p>
          </section>)}
      </main>
      <div className="lgside"><img src="/logo.png" alt="BBTS Data Vision" /><h2 className="lgh">Transformando documentos em decisões.</h2>
        <p className="lgtag">Informação confiável, com fonte, versão e página.</p></div>
    </div>)
}
