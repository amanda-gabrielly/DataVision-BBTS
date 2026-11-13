import { api } from '../api'
import { useApp, useAsync } from '../app-context'
import DocCard from '../components/DocCard'
import { Ic } from '../icons'

export default function Salvos() {
  const { tick } = useApp()
  const { data, loading } = useAsync(() => api.documentos({ salvos: 1 }), [tick])
  return (
    <div className="stack">
      <div className="pgh"><div><h2>Salvos</h2><p>Documentos que você marcou com a bandeirinha.</p></div></div>
      {loading ? <div className="skel" style={{ height: 160 }} />
        : data?.length ? <div className="fgrid">{data.map((d) => <DocCard key={d.id} doc={d} />)}</div>
        : <div className="card empty"><Ic n="flag" s={32} /><p>Nada salvo ainda. Use a bandeirinha em qualquer documento.</p></div>}
    </div>)
}
