import { useEffect, useState } from 'react'
import { api } from '../api'
import { go, useApp, useAsync } from '../app-context'
import { Ic } from '../icons'
import { CLASSIF, fmtData, mergeChunks } from '../util'
import { ClassPill, StatusPill } from '../ui'

export default function DocDrawer({ id, pagina, versao, onClose }) {
  const { me, openDoc, toggleSalvo, tick, refresh, toast } = useApp()
  const { data: doc, loading, error } = useAsync(() => api.documento(id), [id, tick])
  const [vSel, setVId] = useState(null)
  const [pg, setPg] = useState(pagina || 1)
  const [texto, setTexto] = useState('')
  const padrao = doc && ((versao && doc.versoes.find((v) => v.versao === versao)) || doc.versoes.find((v) => v.status === 'vigente') || doc.versoes[0])
  const vId = vSel ?? padrao?.id

  useEffect(() => {
    if (!vId) return
    api.trechos(id, vId, pg).then((r) => setTexto(mergeChunks(r.trechos.map((t) => t.conteudo)))).catch(() => setTexto(''))
  }, [id, vId, pg])
  useEffect(() => {
    const k = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k)
  }, [onClose])

  const ver = doc?.versoes.find((v) => v.id === vId)
  return (
    <div className="scrim" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label="Detalhes do documento" onClick={(e) => e.stopPropagation()}>
        {loading && <div className="skel" style={{ height: 120 }} />}
        {error && <div className="alert bad">{error.message}</div>}
        {doc && (<>
          <div className="ch2" style={{ marginBottom: 0 }}>
            <div><small>{doc.codigo} · {doc.tipo} · {doc.pasta_nome}</small><h2>{doc.titulo}</h2></div>
            <button className="iconbtn" onClick={onClose} aria-label="Fechar"><Ic n="x" /></button>
          </div>
          <div className="fv" style={{ margin: '8px 0' }}>
            <ClassPill c={doc.classificacao} />
            {me?.perfil?.admin && (
              <select className="inp" style={{ width: 'auto' }} aria-label="Reclassificar documento" value={doc.classificacao}
                onChange={async (e) => { try { await api.reclassificar(doc.id, e.target.value); toast('Classificação atualizada'); refresh() } catch (x) { toast(x.message) } }}>
                {Object.entries(CLASSIF).map(([k, c]) => <option key={k} value={k}>{c.nome}</option>)}
              </select>)}
          </div>
          <div className="tools">
            <button className="btn sm" onClick={() => { onClose(); go(`perguntar?doc=${doc.id}`) }}><Ic n="chat" s={16} />Perguntar sobre este documento</button>
            <button className="btn g sm" onClick={() => { onClose(); go(`relatorios/${doc.id}`) }}><Ic n="chart" s={16} />Ver relatório</button>
            <button className="btn g sm" onClick={() => toggleSalvo(doc)}><Ic n="flag" s={16} />{doc.salvo ? 'Salvo' : 'Salvar'}</button>
          </div>
          <section>
            <h3 style={{ marginBottom: 10 }}>Versões</h3>
            {doc.versoes.some((v) => v.status !== 'vigente') && (
              <div className="alert" style={{ marginBottom: 12 }}><Ic n="alert" s={18} />Este documento tem versões anteriores. Consulte sempre a versão em vigor.</div>)}
            <div className="tl">
              {doc.versoes.map((v) => (
                <div key={v.id} className={'tli' + (v.status === 'vigente' ? ' cur' : '')}>
                  <div className="vn">v{v.versao.split('.')[0]}</div>
                  <div>
                    <div className="fv"><b>Versão {v.versao}</b><StatusPill status={v.status} /></div>
                    <small>{v.vigencia_inicio ? `Vigência ${fmtData(v.vigencia_inicio)} a ${fmtData(v.vigencia_fim)}` : v.data_documento ? `Em ${fmtData(v.data_documento)}` : '—'}
                      {v.elaborado_por ? ` · ${v.elaborado_por}` : ''}</small>
                    <div><button className="btn g sm" style={{ marginTop: 6 }} onClick={() => { setVId(v.id); setPg(1) }}>Ler esta versão</button></div>
                  </div>
                </div>))}
            </div>
          </section>
          {ver && (
            <section>
              <div className="ch2"><h3>Texto · versão {ver.versao}</h3><StatusPill status={ver.status} /></div>
              <div className="pg" role="tablist" aria-label="Páginas">
                {Array.from({ length: ver.paginas }, (_, i) => i + 1).map((p) => (
                  <button key={p} className={p === pg ? 'on' : ''} onClick={() => setPg(p)}>{p}</button>))}
              </div>
              <div className="excerpt" style={{ marginTop: 10 }} aria-live="polite">{texto || 'Sem texto nesta página.'}</div>
              <small>Fonte: {doc.codigo} v{ver.versao}, p. {pg} · {ver.arquivo_nome}</small>
            </section>)}
          {doc.relacionados?.length > 0 && (
            <section>
              <h3 style={{ marginBottom: 8 }}>Documentos relacionados</h3>
              <div className="scope">
                {doc.relacionados.map((r) => <button key={r.id} className="sp2" onClick={() => { setVId(null); setPg(1); openDoc(r.id) }}>{r.codigo} · {r.tipo}</button>)}
              </div>
            </section>)}
        </>)}
      </aside>
    </div>
  )
}
