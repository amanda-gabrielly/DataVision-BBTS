import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useApp, useAsync } from '../app-context'
import { Ic } from '../icons'
import { Markdown, StatusPill } from '../ui'

export default function Perguntar({ route }) {
  const { openDoc, tick } = useApp()
  const docId = route.q.get('doc') ? +route.q.get('doc') : null
  const [q, setQ] = useState(route.q.get('q') || '')
  const [pasta, setPasta] = useState('')
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const { data: pastas } = useAsync(() => api.pastas(), [])
  const { data: doc } = useAsync(() => (docId ? api.documento(docId) : Promise.resolve(null)), [docId])
  const { data: hist } = useAsync(() => api.consultas(), [res, tick])
  const first = useRef(true)

  async function enviar(texto = q) {
    if (texto.trim().length < 5) return
    setBusy(true); setErr(null)
    try { setRes(await api.perguntar({ pergunta: texto.trim(), pasta: pasta || null, documento_id: docId })) }
    catch (e) { setErr(e.message); setRes(null) }
    setBusy(false)
  }
  useEffect(() => { // pergunta vinda do painel (?q=)
    if (first.current && route.q.get('q')) enviar(route.q.get('q'))
    first.current = false
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const abrirCitacao = ({ codigo, versao, pagina }) => {
    const f = res?.fontes.find((x) => x.codigo === codigo && x.versao === versao && x.pagina === pagina) || res?.fontes.find((x) => x.codigo === codigo)
    if (f) openDoc(f.documento_id, { pagina, versao })
  }

  return (
    <div className="stack">
      <div className="pgh"><div><h2>Perguntar à IA</h2>
        <p>{doc ? <>Respondendo só com base em <b>{doc.codigo} · {doc.titulo}</b>. <a href="#/perguntar">Remover filtro</a></> : 'Pergunte sobre qualquer documento do acervo.'}</p></div></div>
      <form className="card stack" onSubmit={(e) => { e.preventDefault(); enviar() }}>
        <div className="askbox" style={{ border: '1px solid var(--line)' }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Digite sua pergunta…" aria-label="Sua pergunta" />
          <button className="btn" disabled={busy || q.trim().length < 5}>{busy ? 'Buscando…' : 'Perguntar'}</button>
        </div>
        {!docId && (
          <div className="scope" style={{ margin: 0 }} role="group" aria-label="Escopo da pergunta">
            <button type="button" className={'sp2' + (!pasta ? ' on' : '')} onClick={() => setPasta('')}>Todas as pastas</button>
            {pastas?.filter((p) => p.documentos > 0).map((p) => (
              <button type="button" key={p.slug} className={'sp2' + (pasta === p.slug ? ' on' : '')} onClick={() => setPasta(p.slug)}>
                <span className="dot" style={{ background: p.cor }} />{p.nome}</button>))}
          </div>)}
      </form>

      <div className="row c32">
        <div className="stack">
          {err && <div className="alert bad"><Ic n="alert" />{err}</div>}
          {busy && <div className="card skel" style={{ height: 160 }} />}
          {res && !busy && (<>
            <section className="card ans" aria-live="polite">
              <div className="ch2" style={{ marginBottom: 0 }}><h3>Resposta</h3>
                <span className="fv">
                  {res.comparacao && <span className="pill">Comparação entre documentos</span>}
                  <span className={'pill ' + (res.modo === 'bedrock' ? 'ok' : 'warn')}>{res.modo === 'bedrock' ? 'IA generativa' : 'Modo offline'}</span></span></div>
              {!res.suficiente && <div className="alert"><Ic n="alert" />Não há evidência suficiente nos documentos para responder com segurança.</div>}
              <Markdown text={res.resposta} onCite={abrirCitacao} />
              <small>Confira a fonte antes de decidir. A resposta não substitui a validação humana.</small>
            </section>
            {res.fontes.length > 0 && (() => {
              const cit = res.fontes.filter((f) => f.citado)
              const principais = cit.length ? cit : res.fontes.slice(0, 3)
              const outras = res.fontes.filter((f) => !principais.includes(f))
              const card = (f) => (
                <div key={f.trecho_id} className={'src' + (f.citado ? ' cited' : '')}>
                  <div className="ch2" style={{ marginBottom: 0 }}>
                    <div className="fv"><b>{f.codigo} v{f.versao}</b><StatusPill status={f.status} /><span className="pill">p. {f.pagina}</span></div>
                    <button className="btn g sm" onClick={() => openDoc(f.documento_id, { pagina: f.pagina, versao: f.versao })}>Abrir na página</button></div>
                  <small>{f.titulo}</small>
                  <div className="q">{f.trecho.length > 420 ? f.trecho.slice(0, 420) + '…' : f.trecho}</div>
                </div>)
              return (
                <section className="stack" aria-label="Fontes"><h3>{cit.length ? 'Fontes da resposta' : 'Fontes'} ({principais.length})</h3>
                  {principais.map(card)}
                  {outras.length > 0 && <details className="rsm-d"><summary>Ver outras {outras.length} fontes consultadas</summary><div className="stack" style={{ marginTop: 10 }}>{outras.map(card)}</div></details>}
                </section>)
            })()}
          </>)}
          {!res && !busy && !err && <div className="card empty"><Ic n="chat" s={32} /><p>Sua resposta aparece aqui, com as fontes.</p></div>}
        </div>
        <aside className="card" style={{ alignSelf: 'start' }}>
          <h3 style={{ marginBottom: 8 }}>Histórico</h3>
          {hist?.length ? <div className="hist">{[...new Map(hist.map((h) => [h.pergunta, h])).values()].slice(0, 10).map((h) => (
            <button key={h.id} onClick={() => { setQ(h.pergunta); enviar(h.pergunta) }}>{h.pergunta}</button>))}</div>
            : <p className="mut">Nenhuma pergunta ainda.</p>}
        </aside>
      </div>
    </div>
  )
}
