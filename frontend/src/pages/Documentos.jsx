import { api } from '../api'
import { go, useApp, useAsync } from '../app-context'
import DocCard from '../components/DocCard'
import { FolderArt, Ic } from '../icons'

export default function Documentos({ route }) {
  const { tick, openUpload } = useApp()
  const slug = route.parts[1]
  const q = route.q.get('q') || ''
  const { data: pastas } = useAsync(() => api.pastas(), [tick])
  const { data: docs, loading, error } = useAsync(
    () => (slug || q ? api.documentos({ pasta: slug !== 'todos' ? slug : '', q }) : Promise.resolve([])), [slug, q, tick])
  const pasta = pastas?.find((p) => p.slug === slug)

  if (!slug && !q) {
    return (
      <div className="stack">
        <div className="pgh"><div><h2>Documentos</h2><p>Escolha uma pasta para ver os arquivos.</p></div>
          <button className="btn" onClick={openUpload}><Ic n="upload" s={18} />Enviar documento</button></div>
        <div className="fgrid">
          {pastas?.map((p) => (
            <a key={p.slug} className="fcard" style={{ '--fc': p.cor }} href={`#/documentos/${p.slug}`}>
              <FolderArt color={p.cor} />
              <div><b>{p.nome}</b><small>{p.descricao}</small><br /><small>{p.documentos} {p.documentos === 1 ? 'documento' : 'documentos'}</small></div>
              {p.com_versoes > 0 && <span className="pill warn"><Ic n="layers" s={14} />{p.com_versoes} com mais de uma versão</span>}
            </a>))}
        </div>
      </div>)
  }
  return (
    <div className="stack">
      <div className="fh2">
        <button className="iconbtn" onClick={() => go('documentos')} aria-label="Voltar às pastas"><Ic n="back" /></button>
        <div><h2>{q ? `Resultados para “${q}”` : pasta?.nome || 'Pasta'}</h2><small>{pasta?.descricao}</small></div>
      </div>
      {error && <div className="alert bad"><Ic n="alert" />{error.message}</div>}
      {loading ? <div className="fgrid">{[0, 1, 2].map((i) => <div key={i} className="skel" style={{ height: 190 }} />)}</div>
        : docs?.length ? <div className="fgrid">{docs.map((d) => <DocCard key={d.id} doc={d} />)}</div>
        : <div className="card empty"><Ic n="folder" s={32} /><p>Nenhum documento aqui ainda.</p>
            <button className="btn" style={{ marginTop: 12 }} onClick={openUpload}>Enviar o primeiro</button></div>}
    </div>)
}
