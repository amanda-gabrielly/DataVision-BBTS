import { useRef, useState } from 'react'
import { api } from '../api'
import { useApp, useAsync } from '../app-context'
import { CLASSIF } from '../util'
import { Ic } from '../icons'

export default function UploadModal({ onClose }) {
  const { data: pastas } = useAsync(() => api.pastas(), [])
  const { me } = useApp()
  const [pasta, setPasta] = useState('')
  const [classif, setClassif] = useState('')
  const [itens, setItens] = useState([])
  const [busy, setBusy] = useState(false)
  const [over, setOver] = useState(false)
  const input = useRef()

  async function enviar(files) {
    const pdfs = [...files]
    if (!pdfs.length) return
    setBusy(true)
    for (const f of pdfs) {
      const item = { nome: f.name }
      setItens((l) => [...l, item])
      try {
        const r = await api.enviar(f, pasta, classif)
        Object.assign(item, r.duplicado ? { estado: 'dup', msg: 'Já estava no acervo' }
          : { estado: 'ok', msg: `${r.codigo} v${r.versao} · ${r.trechos} trechos indexados${r.paginas_sem_texto ? ` · ${r.paginas_sem_texto} pág. sem texto` : ''}` })
      } catch (e) { Object.assign(item, { estado: 'erro', msg: e.message }) }
      setItens((l) => [...l])
    }
    setBusy(false)
  }
  return (
    <div className="scrim mid" onClick={onClose}>
      <div className="modal" role="dialog" aria-label="Enviar documentos" onClick={(e) => e.stopPropagation()}>
        <div className="ch2" style={{ marginBottom: 0 }}><h2>Enviar documentos</h2>
          <button className="iconbtn" onClick={onClose} aria-label="Fechar"><Ic n="x" /></button></div>
        <div>
          <label className="f" htmlFor="up-pasta">Pasta</label>
          <select id="up-pasta" className="inp" value={pasta} onChange={(e) => setPasta(e.target.value)}>
            <option value="">Automática (pela referência do documento)</option>
            {pastas?.map((p) => <option key={p.slug} value={p.slug}>{p.nome}</option>)}
          </select>
        </div>
        <div>
          <label className="f" htmlFor="up-cl">Classificação de acesso</label>
          <select id="up-cl" className="inp" value={classif} onChange={(e) => setClassif(e.target.value)}>
            <option value="">Conforme a capa do PDF (padrão: interna)</option>
            {Object.entries(CLASSIF).filter(([, c]) => c.nivel <= (me?.perfil?.nivel ?? 1)).map(([k, c]) => <option key={k} value={k}>{c.nome}</option>)}
          </select>
        </div>
        <div className={'drop' + (over ? ' on' : '')} role="button" tabIndex={0}
          onClick={() => input.current.click()} onKeyDown={(e) => e.key === 'Enter' && input.current.click()}
          onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); enviar(e.dataTransfer.files) }}>
          <Ic n="upload" s={28} /><p><b>Arraste PDFs aqui</b> ou clique para escolher</p>
          <small>Código, versão e vigência são lidos da capa do PDF. Até 20 MB por arquivo.</small>
          <input ref={input} type="file" accept="application/pdf" multiple hidden onChange={(e) => enviar(e.target.files)} />
        </div>
        {itens.map((i, k) => (
          <div className="upl" key={k}><div><b>{i.nome}</b><br /><small>{i.msg || 'Processando…'}</small></div>
            <span className={'pill ' + (i.estado === 'ok' ? 'ok' : i.estado === 'erro' ? 'bad' : i.estado === 'dup' ? 'warn' : '')}>
              {i.estado === 'ok' ? 'Indexado' : i.estado === 'erro' ? 'Erro' : i.estado === 'dup' ? 'Duplicado' : '…'}</span></div>))}
        <div className="tools" style={{ justifyContent: 'flex-end' }}><button className="btn" onClick={onClose} disabled={busy}>Concluir</button></div>
      </div>
    </div>
  )
}
