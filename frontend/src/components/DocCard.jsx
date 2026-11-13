import { go } from '../app-context'
import { useApp } from '../app-context'
import { Ic } from '../icons'
import { ClassPill, StatusPill } from '../ui'

export default function DocCard({ doc }) {
  const { openDoc, toggleSalvo } = useApp()
  const subst = doc.versoes.filter((v) => v.status !== 'vigente').length
  return (
    <article className="file">
      <div className="fl">
        <span className="fv"><span className="pdf">PDF</span><ClassPill c={doc.classificacao} /></span>
        <button className={'flag' + (doc.salvo ? ' on' : '')} onClick={() => toggleSalvo(doc)}
          aria-pressed={doc.salvo} title={doc.salvo ? 'Remover dos salvos' : 'Salvar'}><Ic n="flag" /></button>
      </div>
      <div><small>{doc.codigo} · {doc.tipo}</small><h3>{doc.titulo}</h3></div>
      <div className="fv">
        <span className="pill ok">Em vigor v{doc.versao_vigente}</span>
        {subst > 0 && <span className="pill warn" title="Existem versões anteriores substituídas"><Ic n="layers" s={14} />{doc.versoes.length} versões</span>}
        <small>{doc.paginas} pág.</small>
      </div>
      <div className="fa">
        <button className="btn sm" onClick={() => openDoc(doc.id)}>Abrir</button>
        <button className="btn g sm" onClick={() => go(`relatorios/${doc.id}`)}><Ic n="chart" s={16} />Relatório</button>
        <button className="btn g sm" onClick={() => go(`perguntar?doc=${doc.id}`)}><Ic n="chat" s={16} />Perguntar</button>
      </div>
    </article>
  )
}
export { StatusPill }
