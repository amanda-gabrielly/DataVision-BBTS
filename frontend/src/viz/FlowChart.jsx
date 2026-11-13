import { useMemo } from 'react'
import { layoutFlow, NH, NW } from './layoutFlow'

const COR = { inicio: '#01B8AA', fim: '#A66999', decisao: '#F2C811', prazo: '#FE9666', etapa: '#3599B8' }
const isPrazo = (n) => /\bD-\d+|até|dias?\b|\d{2}\/\d{2}/i.test(n.rotulo)

export default function FlowChart({ fluxo, sel, onSel }) {
  const L = useMemo(() => layoutFlow(fluxo.nos, fluxo.arestas), [fluxo])
  const cor = (n) => (n.tipo === 'etapa' && isPrazo(n) ? COR.prazo : COR[n.tipo] || COR.etapa)

  const edge = (e, i) => {
    const a = L.pos[e.de], b = L.pos[e.para]
    if (!a || !b) return null
    const isBack = L.back.has(e)
    let d, lx, ly
    if (isBack) {
      const sx = a.x, sy = a.y + NH / 2, tx = b.x, ty = b.y + NH / 2, o = 80
      d = `M${sx},${sy} C${sx - o},${sy} ${tx - o},${ty} ${tx},${ty}`
      lx = Math.min(sx, tx) - o * 0.75 - 8; ly = (sy + ty) / 2
    } else {
      const sx = a.x + NW / 2, sy = a.y + NH, tx = b.x + NW / 2, ty = b.y, k = Math.max(24, (ty - sy) / 2)
      d = `M${sx},${sy} C${sx},${sy + k} ${tx},${ty - k} ${tx},${ty}`
      ly = sy + Math.max(18, (ty - sy) * 0.3)
      lx = tx === sx ? sx : sx + (tx - sx) * 0.35
    }
    return (
      <g key={i}>
        <path className={'fe' + (isBack ? ' back' : '')} d={d} markerEnd="url(#arr)" />
        {e.rotulo && <text className="fl-lab" x={lx} y={ly} textAnchor={isBack ? 'end' : 'middle'}>{e.rotulo}</text>}
      </g>
    )
  }

  return (
    <div className="canvas" role="group" aria-label="Fluxograma">
      <svg width={L.width} height={L.height} viewBox={`0 0 ${L.width} ${L.height}`} style={{ maxWidth: 'none' }}>
        <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="var(--mut)" /></marker></defs>
        {fluxo.arestas.map(edge)}
        {fluxo.nos.map((n) => {
          const p = L.pos[n.id]; const on = sel?.key === 'n' + n.id
          const k = cor(n)
          return (
            <g key={n.id} className={`fn ${n.tipo}${on ? ' on' : ''}`} style={{ '--k': k }} tabIndex={0} role="button" aria-label={n.rotulo}
              onClick={() => onSel({ key: 'n' + n.id, titulo: n.rotulo, ref: n.ref, pagina: n.pagina, trecho: n.rotulo })}
              onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.dispatchEvent(new MouseEvent('click', { bubbles: true }))}>
              {n.tipo === 'decisao'
                ? <polygon className="box" points={`${p.x + 22},${p.y} ${p.x + NW - 22},${p.y} ${p.x + NW},${p.y + NH / 2} ${p.x + NW - 22},${p.y + NH} ${p.x + 22},${p.y + NH} ${p.x},${p.y + NH / 2}`} />
                : <rect className="box" x={p.x} y={p.y} width={NW} height={NH} rx={n.tipo === 'inicio' || n.tipo === 'fim' ? NH / 2 : 10} />}
              <foreignObject x={p.x + 6} y={p.y} width={NW - 12} height={NH}><div>{n.rotulo}</div></foreignObject>
            </g>)
        })}
      </svg>
      <div className="fv" style={{ padding: '10px 14px', borderTop: '1px solid var(--line)' }}>
        {[['Início', COR.inicio], ['Etapa', COR.etapa], ['Prazo / marco', COR.prazo], ['Decisão', COR.decisao], ['Fim', COR.fim]].map(([t, c]) => (
          <small key={t}><span className="dot" style={{ background: c, marginRight: 6 }} />{t}</small>))}
        <small>· linha tracejada = retorno a uma etapa anterior</small>
        {fluxo.legenda && <small>· {fluxo.legenda}</small>}
      </div>
    </div>
  )
}
