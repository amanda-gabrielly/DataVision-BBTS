import { useState } from 'react'
import { api } from '../api'
import { go, useApp, useAsync } from '../app-context'
import { FolderArt, Ic } from '../icons'

export default function Painel() {
  const { me, tick } = useApp()
  const { data, loading, error } = useAsync(() => api.painel(), [tick])
  const [q, setQ] = useState('')
  const ask = (text) => text.trim().length >= 5 && go(`perguntar?q=${encodeURIComponent(text.trim())}`)
  if (error) return <div className="alert bad"><Ic n="alert" />Não consegui falar com a API. Verifique se o backend está no ar. ({error.message})</div>
  const n = data?.numeros
  return (
    <div className="stack">
      <section className="card ask" aria-labelledby="ask-h">
        <div><h2 id="ask-h">Olá, {me?.nome?.split(' ')[0] || 'bem-vindo'}! O que você precisa saber?</h2>
          <p>Pergunte em linguagem natural. Toda resposta traz documento, versão e página.</p></div>
        <form className="askbox" onSubmit={(e) => { e.preventDefault(); ask(q) }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ex.: qual a antecedência mínima para solicitar férias?" aria-label="Sua pergunta" />
          <button className="btn y" type="submit">Perguntar</button>
        </form>
        <div className="chips">{data?.sugestoes.map((s) => <button key={s} className="chip" onClick={() => ask(s)}>{s}</button>)}</div>
      </section>

      {data?.perfil && (
        <div className="alert" role="note"><Ic n="user" s={18} />
          <span>Seu perfil: <b>{data.perfil.nome}</b> — {data.perfil.descricao}.
            {n?.fora_do_perfil > 0 && <> {n.fora_do_perfil} documento(s) do acervo não aparecem para você.</>}</span>
        </div>)}

      <section className="row c4" aria-label="Indicadores">
        {loading ? [0, 1, 2, 3].map((i) => <div key={i} className="card skel" style={{ height: 92 }} />) : (<>
          <div className="card kpi"><b>{n.documentos}</b><span>documentos no acervo</span></div>
          <div className={'card kpi' + (n.substituidas ? ' w' : '')}><b>{n.substituidas}</b><span>versões substituídas (atenção)</span></div>
          <div className="card kpi"><b>{n.trechos}</b><span>trechos indexados</span></div>
          <div className="card kpi"><b>{n.consultas}</b><span>perguntas já feitas</span></div></>)}
      </section>

      <section>
        <div className="ch2"><h3>Pastas</h3><a className="btn g sm" href="#/documentos">Ver todas</a></div>
        <div className="fgrid">
          {data?.pastas.filter((p) => p.slug !== 'geral' || p.documentos > 0).map((p) => (
            <a key={p.slug} className="fcard" style={{ '--fc': p.cor }} href={`#/documentos/${p.slug}`}>
              <FolderArt color={p.cor} />
              <div><b>{p.nome}</b><small>{p.documentos} {p.documentos === 1 ? 'documento' : 'documentos'}</small></div>
              {p.com_versoes > 0 && <span className="pill warn"><Ic n="layers" s={14} />{p.com_versoes} com mais de uma versão</span>}
            </a>))}
        </div>
      </section>

      <section className="row c2">
        <div className="card">
          <div className="ch2"><h3>Perguntas recentes</h3></div>
          {data?.recentes.length ? (
            <div className="hist">{data.recentes.map((r) => <button key={r.id} onClick={() => ask(r.pergunta)}>{r.pergunta}</button>)}</div>
          ) : <p className="mut">Suas perguntas aparecem aqui.</p>}
        </div>
        <div className="card">
          <div className="ch2"><h3>Como a IA está respondendo</h3>
            <span className={'pill ' + (data?.ia === 'bedrock' ? 'ok' : 'warn')}>{data?.ia === 'bedrock' ? 'Amazon Bedrock' : 'Modo offline'}</span></div>
          <p className="mut">{data?.ia === 'bedrock'
            ? 'Respostas geradas pelo Amazon Nova Lite a partir dos trechos mais próximos (busca semântica).'
            : 'Sem credenciais AWS: a busca é textual e a resposta mostra os trechos encontrados, sem texto gerado. Ative o Bedrock para respostas completas.'}</p>
        </div>
      </section>
    </div>
  )
}
