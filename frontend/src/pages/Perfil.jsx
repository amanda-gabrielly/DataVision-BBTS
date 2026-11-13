import { useRef, useState } from 'react'
import { api } from '../api'
import { useApp } from '../app-context'
import { Ic } from '../icons'
import { iniciais } from '../util'

// Reduz a foto para 256px (JPEG) antes de enviar: leve e sem depender de armazenamento de arquivos.
function reduzir(file) {
  return new Promise((ok, fail) => {
    const img = new Image()
    img.onload = () => {
      const s = Math.min(256 / img.width, 256 / img.height, 1)
      const c = document.createElement('canvas'); c.width = img.width * s; c.height = img.height * s
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height)
      ok(c.toDataURL('image/jpeg', 0.85))
    }
    img.onerror = () => fail(new Error('Imagem inválida.'))
    img.src = URL.createObjectURL(file)
  })
}

export default function Perfil() {
  const { me } = useApp()
  return me ? <PerfilForm me={me} /> : <div className="skel" style={{ height: 200 }} />
}

function PerfilForm({ me }) {
  const { setMe, toast, theme, setTheme } = useApp()
  const [f, setF] = useState(() => ({ ...me, preferencias: me.preferencias || {} }))
  const file = useRef()
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const pref = (k) => (e) => setF({ ...f, preferencias: { ...f.preferencias, [k]: e.target.checked } })

  async function salvar() {
    try { setMe(await api.atualizarMe({ nome: f.nome, cargo: f.cargo, area: f.area, telefone: f.telefone, localizacao: f.localizacao, foto: f.foto, preferencias: f.preferencias })); toast('Perfil salvo') }
    catch (e) { toast(e.message) }
  }
  async function foto(e) {
    const fl = e.target.files[0]; if (!fl) return
    try { setF({ ...f, foto: await reduzir(fl) }) } catch (er) { toast(er.message) }
  }
  return (
    <div className="stack" style={{ maxWidth: 820 }}>
      <section className="card" style={{ padding: 0 }}>
        <div className="pcv" />
        <div className="pbd">
          <div className="pav">{f.foto ? <img src={f.foto} alt="Sua foto" /> : iniciais(f.nome)}</div>
          <div className="pn"><h2>{f.nome}</h2><p className="mut">{f.cargo || 'Cargo não informado'}{f.area ? ` · ${f.area}` : ''}</p></div>
          <div className="pa">
            <button className="btn g" onClick={() => file.current.click()}><Ic n="camera" s={18} />Trocar foto</button>
            {f.foto && <button className="btn g" onClick={() => setF({ ...f, foto: null })}>Remover</button>}
            <input ref={file} type="file" accept="image/*" hidden onChange={foto} />
          </div>
        </div>
      </section>
      <section className="card">
        <h3 style={{ marginBottom: 14 }}>Dados pessoais</h3>
        <div className="fg">
          {[['nome', 'Nome'], ['cargo', 'Cargo'], ['area', 'Área'], ['telefone', 'Telefone'], ['localizacao', 'Localização']].map(([k, l]) => (
            <div key={k}><label className="f" htmlFor={'p-' + k}>{l}</label><input id={'p-' + k} className="inp" value={f[k] || ''} onChange={set(k)} /></div>))}
          <div><label className="f" htmlFor="p-email">E-mail</label><input id="p-email" className="inp" value={f.email} disabled /></div>
        </div>
      </section>
      <section className="card">
        <h3 style={{ marginBottom: 6 }}>Preferências</h3>
        <div className="swr"><div><b>Tema escuro</b><br /><small>Aplica na hora neste navegador.</small></div>
          <label className="sw"><input type="checkbox" checked={theme === 'dark'} onChange={(e) => setTheme(e.target.checked ? 'dark' : 'light')} /><i /></label></div>
        <div className="swr"><div><b>Avisar quando um documento salvo ganhar nova versão</b></div>
          <label className="sw"><input type="checkbox" checked={!!f.preferencias.avisar_versao} onChange={pref('avisar_versao')} /><i /></label></div>
        <div className="swr"><div><b>Mostrar versões substituídas nas respostas</b></div>
          <label className="sw"><input type="checkbox" checked={!!f.preferencias.mostrar_substituidas} onChange={pref('mostrar_substituidas')} /><i /></label></div>
      </section>
      <TrocarSenha />
      <div className="tools"><button className="btn" onClick={salvar}>Salvar alterações</button></div>
    </div>)
}

function TrocarSenha() {
  const { toast } = useApp()
  const [atual, setAtual] = useState('')
  const [nova, setNova] = useState('')
  async function trocar(e) {
    e.preventDefault()
    try { await api.trocarSenha(atual, nova); setAtual(''); setNova(''); toast('Senha alterada') }
    catch (x) { toast(x.message) }
  }
  return (
    <form className="card" onSubmit={trocar}>
      <h3 style={{ marginBottom: 14 }}>Alterar senha</h3>
      <div className="fg">
        <div><label className="f" htmlFor="s-atual">Senha atual</label>
          <input id="s-atual" className="inp" type="password" autoComplete="current-password" value={atual} onChange={(e) => setAtual(e.target.value)} required /></div>
        <div><label className="f" htmlFor="s-nova">Nova senha (mínimo 8 caracteres)</label>
          <input id="s-nova" className="inp" type="password" autoComplete="new-password" minLength={8} value={nova} onChange={(e) => setNova(e.target.value)} required /></div>
      </div>
      <div className="tools" style={{ marginTop: 14 }}><button className="btn g" type="submit">Alterar senha</button></div>
    </form>)
}
