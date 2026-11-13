export function Donut({ dados, sel, onPick }) {
  const total = dados.reduce((s, d) => s + d.n, 0) || 1
  const R = 80, C = 2 * Math.PI * R
  const offs = dados.reduce((a, d, i) => [...a, i ? a[i - 1] + (dados[i - 1].n / total) * C : 0], [])
  return (
    <div className="pw">
      <svg className="pie" viewBox="0 0 200 200" role="img" aria-label="Itens por perspectiva">
        <g transform="rotate(-90 100 100)">
          {dados.map((d, i) => {
            const len = (d.n / total) * C, off = -offs[i]
            return <circle key={d.k} cx="100" cy="100" r={R} fill="none" stroke={d.cor} strokeWidth={sel === d.k ? 40 : 32}
              strokeDasharray={`${len} ${C - len}`} strokeDashoffset={off} style={{ cursor: 'pointer', transition: '.15s' }} onClick={() => onPick(d.k)} />
          })}
        </g>
        <text x="100" y="98" textAnchor="middle" style={{ font: '800 28px var(--fd)', fill: 'var(--ink)' }}>{total}</text>
        <text x="100" y="118" textAnchor="middle" style={{ font: '12px var(--fb)', fill: 'var(--mut)' }}>itens</text>
      </svg>
      <div className="lgl">
        {dados.map((d) => (
          <button key={d.k} className={'lgi' + (sel === d.k ? ' on' : '')} onClick={() => onPick(d.k)}>
            <i style={{ background: d.cor }} /><span>{d.nome}</span><b>{d.n}</b></button>))}
      </div>
    </div>)
}

export function PrazoBars({ prazos, sel, onSel }) {
  if (!prazos.length) return <p className="mut">Este documento não traz prazos em dias, meses ou anos.</p>
  const lista = [...prazos].sort((a, b) => b.dias - a.dias)
  const max = Math.max(...lista.map((p) => p.dias), 1)
  const row = 36, lw = 250, W = 560
  return (
    <svg viewBox={`0 0 ${W} ${lista.length * row + 8}`} style={{ width: '100%', height: 'auto' }} role="img" aria-label="Prazos em dias">
      {lista.map((p, i) => {
        const w = Math.max(4, ((W - lw - 100) * p.dias) / max), on = sel === 'p' + p.ref
        const t = p.rotulo.length > 30 ? p.rotulo.slice(0, 29) + '…' : p.rotulo
        return (
          <g key={p.ref + i} className={'bk' + (on ? ' on' : '')} transform={`translate(0 ${i * row + 4})`} tabIndex={0} role="button"
            onClick={() => onSel({ key: 'p' + p.ref, titulo: p.rotulo, ref: p.ref, pagina: p.pagina, trecho: `${p.rotulo}: ${p.texto}` })}>
            <text x={lw - 10} y="20" textAnchor="end" style={{ font: '14px var(--fb)', fill: 'var(--ink)' }}>{t}</text>
            <rect x={lw} y="4" width={w} height="24" rx="4" fill="#01B8AA" />
            <text x={lw + w + 8} y="20" style={{ font: '700 14px var(--fb)', fill: 'var(--ink)' }}>{p.texto}</text>
          </g>)
      })}
    </svg>)
}
