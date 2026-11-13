import { useMemo, useState } from 'react'
import { api } from '../api'
import { go, useApp, useAsync } from '../app-context'
import { Ic } from '../icons'
import { PAL, PERSP, perspDados } from '../util'
import { StatusPill } from '../ui'
import { Donut, PrazoBars } from '../viz/Charts'
import FlowChart from '../viz/FlowChart'
import MindMap from '../viz/MindMap'

const VISOES = [
  ['painel', 'Painel', 'grid'], ['graficos', 'Gráficos', 'chart'], ['fluxo', 'Fluxograma', 'flow'],
  ['mapa', 'Mapa mental', 'tree'], ['info', 'Infográfico', 'info'], ['quadro', 'Quadro', 'table'],
]

function Escolher() {
  const { tick } = useApp()
  const { data: docs } = useAsync(() => api.documentos(), [tick])
  const grupos = useMemo(() => {
    const g = {}
    docs?.forEach((d) => { (g[d.pasta_nome] ||= { cor: d.cor, itens: [] }).itens.push(d) })
    return g
  }, [docs])
  return (
    <div className="stack">
      <div className="pgh"><div><h2>Relatórios</h2><p>Escolha um documento para ver painel, gráficos, fluxograma, mapa mental, infográfico e quadro, todos ligados à fonte.</p></div></div>
      {Object.entries(grupos).map(([nome, g]) => (
        <section key={nome}><h3 style={{ marginBottom: 10 }}><span className="dot" style={{ background: g.cor, marginRight: 8 }} />{nome}</h3>
          <div className="fgrid">{g.itens.map((d) => (
            <button key={d.id} className="fcard" style={{ '--fc': g.cor }} onClick={() => go(`relatorios/${d.id}`)}>
              <div><small>{d.codigo} · {d.tipo}</small><b>{d.titulo}</b></div>
              <span className="pill ok">Em vigor v{d.versao_vigente}</span></button>))}</div></section>))}
    </div>)
}

export default function Relatorios({ route }) {
  const id = route.parts[1] ? +route.parts[1] : null
  return id ? <Relatorio key={id} id={id} /> : <Escolher />
}

function Relatorio({ id }) {
  const { openDoc } = useApp()
  const [vId, setVId] = useState(null)
  const [vis, setVis] = useState('painel')
  const [sel, setSel] = useState(null)
  const [persp, setPersp] = useState('prazos')
  const { data: doc } = useAsync(() => api.documento(id), [id])
  const { data, loading, error } = useAsync(() => api.visoes(id, vId), [id, vId])

  const dados = useMemo(() => data && perspDados(data.grafico), [data])
  const v = data?.versao
  const fonte = sel && { ...sel, codigo: data.documento.codigo, versao: v.versao }

  return (
    <div className="stack">
      <div className="pbi">
        <div className="pbh">
          <div className="pbl"><button className="btn sm pbbk" onClick={() => go('relatorios')}><Ic n="back" s={16} />Documentos</button>
            <div><b>{doc ? `${doc.codigo} · ${doc.titulo}` : '…'}</b><br /><small>Relatório gerado do conteúdo do PDF</small></div></div>
          <div className="pbl">
            {doc && doc.versoes.length > 1 && (
              <select aria-label="Versão" value={v?.id || ''} onChange={(e) => { setVId(+e.target.value); setSel(null) }}>
                {doc.versoes.map((x) => <option key={x.id} value={x.id}>v{x.versao} {x.status === 'vigente' ? '(em vigor)' : '(substituída)'}</option>)}
              </select>)}
            {v && <StatusPill status={v.status} />}
          </div>
        </div>
        <div className="pbw">
          <nav className="pbn" aria-label="Tipos de visualização"><small>VISUALIZAÇÕES</small>
            {VISOES.map(([k, l, ic]) => <button key={k} className={vis === k ? 'on' : ''} onClick={() => { setVis(k); setSel(null) }}><Ic n={ic} s={18} />{l}</button>)}
          </nav>
          <div className="pbc">
            {error && <div className="alert bad"><Ic n="alert" />{error.message}</div>}
            {loading && <div className="skel" style={{ height: 300 }} />}
            {data && v?.status !== 'vigente' && (
              <div className="alert"><Ic n="alert" s={18} />Você está vendo uma versão <b>substituída</b>. Use a versão em vigor para decisões.</div>)}
            {data && !loading && (<>
              {vis === 'painel' && <VPainel data={data} dados={dados} persp={persp} setPersp={setPersp} onSel={setSel} sel={sel} />}
              {vis === 'graficos' && (<>
                <Cab t="Gráficos" s="Prazos do documento em dias e distribuição dos itens por perspectiva. Clique para ver a fonte." />
                <div className="row c2"><div className="pc"><h4>Prazos (em dias corridos)</h4><PrazoBars prazos={data.grafico.prazos} sel={sel?.key} onSel={setSel} /></div>
                  <div className="pc"><h4>Itens por perspectiva</h4><Donut dados={dados} sel={persp} onPick={setPersp} /></div></div></>)}
              {vis === 'fluxo' && (<>
                <Cab t="Fluxograma" s={data.fluxo.origem === 'mermaid' ? 'Fluxo desenhado no próprio documento. Clique em uma etapa para ver a fonte.' : data.fluxo.aviso || ''} />
                {data.fluxo.nos.length ? <FlowChart fluxo={data.fluxo} sel={sel} onSel={setSel} /> : <div className="pc"><p className="mut">{data.fluxo.aviso}</p></div>}
                {data.fluxo.origem === 'prazos' && <div className="alert"><Ic n="info" s={18} />{data.fluxo.aviso}</div>}</>)}
              {vis === 'mapa' && (<><Cab t="Mapa mental" s="Seções do documento. Clique em um ramo para abrir ou fechar e em um item para ver a fonte." /><MindMap mapa={data.mapa} sel={sel} onSel={setSel} /></>)}
              {vis === 'info' && <VInfo data={data} sel={sel} onSel={setSel} />}
              {vis === 'quadro' && <VQuadro data={data} sel={sel} onSel={setSel} />}
            </>)}
            {data && (
              <div className={'srcbar' + (fonte ? '' : ' idle')} aria-live="polite">
                {fonte ? (<>
                  <div><small>FONTE · {fonte.codigo} v{fonte.versao}, p. {fonte.pagina}{fonte.ref ? ` · item ${fonte.ref}` : ''}</small>
                    <b style={{ display: 'block' }}>{fonte.titulo}</b>{fonte.trecho && fonte.trecho !== fonte.titulo && <p>{fonte.trecho}</p>}</div>
                  <button className="btn y sm" onClick={() => openDoc(id, { pagina: fonte.pagina, versao: fonte.versao })}>Abrir na página</button></>)
                  : <span>Selecione um elemento para ver o documento, a versão e a página de origem.</span>}
              </div>)}
          </div>
        </div>
      </div>
    </div>)
}

const Cab = ({ t, s }) => <div className="cvh"><div><h3>{t}</h3><small>{s}</small></div></div>

function VPainel({ data, dados, persp, setPersp, onSel, sel }) {
  const { id } = { id: data.documento.id }
  const { data: res } = useAsync(() => api.resumo(id, persp, data.versao.id), [id, persp, data.versao.id])
  return (<>
    <Cab t="Painel" s={`${data.quadro.length} itens com prazo, valor, obrigação ou risco identificados no texto.`} />
    <div className="row c4">{dados.map((d) => (
      <button key={d.k} className="pc pk" style={{ '--k': d.cor, textAlign: 'left', cursor: 'pointer' }} onClick={() => setPersp(d.k)} aria-pressed={persp === d.k}>
        <b>{d.n}</b><span className="mut">{d.nome}</span></button>))}</div>
    <div className="row c2"><div className="pc"><h4>Itens por perspectiva</h4><Donut dados={dados} sel={persp} onPick={setPersp} /></div>
      <div className="pc"><h4>Prazos</h4><PrazoBars prazos={data.grafico.prazos} sel={sel?.key} onSel={onSel} /></div></div>
    <div className="pc">
      <div className="ch2"><h4 style={{ margin: 0 }}>Resumo por perspectiva: {PERSP[persp].nome}</h4>
        {res && <span className={'pill ' + (res.modo === 'bedrock' ? 'ok' : 'warn')}>{res.modo === 'bedrock' ? 'Resumo por IA' : 'Trechos extraídos'}</span>}</div>
      {res?.resumo && <ul className="rsm">{res.resumo.split('\n').map((l, k) => (
        <li key={k}>{l.replace(/^[-•*]\s*/, '').replace(/\*\*/g, '').replace(/\[[A-Z]+_[\w-]+\s+v[\d.]+,\s*(p\.?\s*\d+)\]/g, '($1)')}</li>))}</ul>}
      {res && (() => {
        const lista = res.itens.length ? <ul style={{ margin: 0, paddingLeft: 18 }}>{res.itens.slice(0, res.resumo ? 8 : 5).map((i) => (
          <li key={i.ref} style={{ marginBottom: 6 }}><button className="cite" onClick={() => onSel({ key: 'r' + i.ref, titulo: `Item ${i.ref}`, ref: i.ref, pagina: i.pagina, trecho: i.texto })}>p. {i.pagina}</button> {i.texto.slice(0, 180)}{i.texto.length > 180 ? '…' : ''}</li>))}</ul>
          : <p className="mut">Nenhum item nesta perspectiva.</p>
        return res.resumo && res.itens.length
          ? <details className="rsm-d"><summary>Ver os trechos de origem ({res.itens.length})</summary>{lista}</details>
          : lista
      })()}
    </div></>)
}

function VInfo({ data, sel, onSel }) {
  return (<>
    <Cab t="Infográfico" s="Os números mais importantes do documento, cada um com a página de origem." />
    {data.numeros.length ? <div className="info2">{data.numeros.map((n, i) => (
      <button key={n.ref + n.valor} className={'tile' + (sel?.key === 'n' + n.ref ? ' on' : '')} style={{ '--k': PAL[i % 7] }}
        onClick={() => onSel({ key: 'n' + n.ref, titulo: `${n.valor} · ${n.contexto}`, ref: n.ref, pagina: n.pagina, trecho: n.contexto })}>
        <span className="big">{n.valor}</span><b>{n.contexto}</b><small>página {n.pagina} · item {n.ref}</small></button>))}</div>
      : <div className="pc"><p className="mut">Não encontrei prazos ou valores neste documento.</p></div>}
  </>)
}

function VQuadro({ data, sel, onSel }) {
  return (<>
    <Cab t="Quadro" s="Itens do documento organizados por perspectiva. Um item pode aparecer em mais de uma coluna." />
    <div className="brd2">{Object.entries(PERSP).map(([k, p]) => {
      const itens = data.quadro.filter((r) => r.perspectivas.includes(k))
      return (
        <div key={k} className="kc"><div className="kh" style={{ background: p.cor }}><span>{p.nome}</span><span>{itens.length}</span></div>
          {itens.slice(0, 14).map((r) => (
            <button key={r.ref + k} className={'kcard' + (sel?.key === `q${k}${r.ref}` ? ' on' : '')} style={{ '--k': p.cor }}
              onClick={() => onSel({ key: `q${k}${r.ref}`, titulo: r.titulo || `Item ${r.ref}`, ref: r.ref, pagina: r.pagina, trecho: r.texto })}>
              <b>{r.destaque || r.titulo || r.ref}</b><p>{r.texto}</p><small>p. {r.pagina} · {r.ref}</small></button>))}
          {itens.length > 14 && <small>+{itens.length - 14} itens</small>}
          {!itens.length && <small>Nenhum item.</small>}</div>)
    })}</div></>)
}
