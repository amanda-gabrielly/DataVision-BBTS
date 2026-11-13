import { useEffect, useMemo, useRef, useState } from 'react'
import { PAL, wrap } from '../util'

const RW = 190, BW = 210, BH = 40, LW = 360, LH = 30, GAP = 10, X1 = 250, X2 = 520

export default function MindMap({ mapa, sel, onSel }) {
  const maior = useMemo(() => mapa.ramos.reduce((m, r) => (r.filhos.length > (m?.filhos.length ?? -1) ? r : m), null), [mapa])
  const total = mapa.ramos.reduce((s, r) => s + r.filhos.length, 0)
  const [open, setOpen] = useState(() => new Set(total <= 14 ? mapa.ramos.map((r) => r.id) : maior ? [maior.id] : []))
  const box = useRef(null)
  const toggle = (id) => setOpen((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  const L = useMemo(() => {
    const alturas = mapa.ramos.map((r) => Math.max(BH + 6, (open.has(r.id) ? r.filhos.length : 0) * (LH + 6)))
    const tops = alturas.reduce((a, h, i) => [...a, i ? a[i - 1] + alturas[i - 1] + GAP : 20], [])
    const y = tops.length ? tops[tops.length - 1] + alturas[alturas.length - 1] + GAP : 20
    const br = mapa.ramos.map((r, i) => {
      const vis = open.has(r.id) ? r.filhos : []
      const top = tops[i], cy = top + alturas[i] / 2
      return { r, i, cy, leaves: vis.map((f, k) => ({ f, cy: top + k * (LH + 6) + LH / 2 })) }
    })
    const rootY = br.length ? (br[0].cy + br[br.length - 1].cy) / 2 : 40
    return { br, rootY, h: Math.max(y, 80) }
  }, [mapa, open])

  useEffect(() => { // centraliza o tema central na janela ao abrir ou expandir
    if (box.current) box.current.scrollTop = Math.max(0, L.rootY - box.current.clientHeight / 2)
  }, [L.rootY, L.h])

  const curve = (x1, y1, x2, y2) => `M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`
  const W = X2 + LW + 20
  const cor = (i) => PAL[i % 7] // sem o cinza-escuro, que não tem contraste com o texto do ramo
  if (!mapa.ramos.length) return <div className="pc"><p className="mut">{mapa.aviso}</p></div>
  const rootLines = wrap(`${mapa.raiz.codigo} · ${mapa.raiz.titulo}`, 20).slice(0, 4)

  return (
    <div>
      <div className="tools" style={{ marginBottom: 8 }}>
        <button className="btn g sm" onClick={() => setOpen(new Set(mapa.ramos.map((r) => r.id)))}>Expandir tudo</button>
        <button className="btn g sm" onClick={() => setOpen(new Set())}>Recolher</button>
      </div>
      <div className="canvas tall" ref={box} role="group" aria-label="Mapa mental">
        <svg width={W} height={L.h + 20} viewBox={`0 0 ${W} ${L.h + 20}`} style={{ maxWidth: 'none' }}>
          {L.br.map(({ r, i, cy, leaves }) => (
            <g key={r.id} style={{ '--k': cor(i) }}>
              <path className="mm-ln" d={curve(RW + 24, L.rootY, X1, cy)} />
              {leaves.map(({ f, cy: ly }) => <path key={f.id} className="mm-ln" d={curve(X1 + BW, cy, X2, ly)} />)}
            </g>))}
          <g className="mm-root">
            <rect x="8" y={L.rootY - 36} width={RW + 16} height="72" rx="18" />
            <text textAnchor="middle" x={8 + (RW + 16) / 2} y={L.rootY - (rootLines.length - 1) * 9 + 5}>
              {rootLines.map((t, k) => <tspan key={k} x={8 + (RW + 16) / 2} dy={k ? 18 : 0}>{t}</tspan>)}</text>
          </g>
          {L.br.map(({ r, i, cy, leaves }) => {
            const k = cor(i), on = sel?.key === 'b' + r.id, lines = wrap(`${/^\d/.test(r.id) ? r.id + '. ' : ''}${r.titulo}`, 24).slice(0, 2)
            return (
              <g key={r.id} style={{ '--k': k }}>
                <g className={'mm-br' + (on ? ' on' : '')} tabIndex={0} role="button" aria-expanded={r.filhos.length ? open.has(r.id) : undefined}
                  onClick={() => { if (r.filhos.length) toggle(r.id); onSel({ key: 'b' + r.id, titulo: r.titulo, ref: r.id, pagina: r.pagina, trecho: r.trecho || '' }) }}
                  onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.dispatchEvent(new MouseEvent('click', { bubbles: true }))}>
                  <rect x={X1} y={cy - BH / 2} width={BW} height={BH} rx="10" />
                  <text x={X1 + 12} y={cy - (lines.length - 1) * 7 + 4}>{lines.map((t, n) => <tspan key={n} x={X1 + 12} dy={n ? 15 : 0}>{t}</tspan>)}</text>
                  {r.filhos.length > 0 && <text className="n" x={X1 + BW - 10} y={cy + 4} textAnchor="end">{open.has(r.id) ? '−' : `+${r.filhos.length}`}</text>}
                </g>
                {leaves.map(({ f, cy: ly }) => {
                  const lon = sel?.key === 'l' + f.id
                  const t = f.titulo.length > 44 ? f.titulo.slice(0, 43) + '…' : f.titulo
                  return (
                    <g key={f.id} className={'mm-lf' + (lon ? ' on' : '')} tabIndex={0} role="button"
                      onClick={() => onSel({ key: 'l' + f.id, titulo: f.titulo, ref: f.id, pagina: f.pagina, trecho: f.trecho })}
                      onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.dispatchEvent(new MouseEvent('click', { bubbles: true }))}>
                      <rect x={X2} y={ly - LH / 2} width={LW} height={LH} rx="8" />
                      <text x={X2 + 10} y={ly + 4}>{f.id} · {t}</text>
                      <text className="pgt" x={X2 + LW - 8} y={ly + 4} textAnchor="end">p.{f.pagina}</text>
                    </g>)
                })}
              </g>)
          })}
        </svg>
      </div>
    </div>
  )
}
