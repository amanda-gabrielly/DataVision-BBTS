import { Fragment } from 'react'

export function ClassPill({ c }) {
  return <span className={'pill cls-' + c} title="Classificação do documento">{{ publica: 'Pública', interna: 'Interna', restrita: 'Restrita', confidencial: 'Confidencial' }[c] || c}</span>
}

export function StatusPill({ status }) {
  return status === 'vigente'
    ? <span className="pill ok">Em vigor</span>
    : <span className="pill warn">Substituída</span>
}

// Renderização mínima de markdown (parágrafos, listas, títulos, **negrito**, tabelas) + citações clicáveis.
const CITE = /\[([A-Z]+_[\w-]+)\s+v([\d.]+),\s*p\.?\s*(\d+)\]/g
function inline(text, onCite, key) {
  const out = []
  let last = 0, m
  const rx = new RegExp(CITE.source, 'g')
  while ((m = rx.exec(text))) {
    if (m.index > last) out.push(...bold(text.slice(last, m.index), `${key}b${last}`))
    const [full, codigo, versao, pagina] = m
    out.push(
      <button key={`${key}c${m.index}`} className="cite" onClick={() => onCite?.({ codigo, versao, pagina: +pagina })}>
        {full.slice(1, -1)}
      </button>
    )
    last = m.index + full.length
  }
  if (last < text.length) out.push(...bold(text.slice(last), `${key}e`))
  return out
}
function bold(text, key) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith('**') && p.endsWith('**') ? <strong key={`${key}${i}`}>{p.slice(2, -2)}</strong> : <Fragment key={`${key}${i}`}>{p}</Fragment>)
}
export function Markdown({ text, onCite }) {
  const lines = text.split('\n')
  const blocks = []
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i]
    if (/^\s*\|/.test(ln) && /^\s*\|[\s:|-]+\|?\s*$/.test(lines[i + 1] || '')) {
      const rows = []
      let j = i
      while (j < lines.length && /^\s*\|/.test(lines[j])) { rows.push(lines[j]); j++ }
      const cells = (r) => r.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
      const head = cells(rows[0]); const body = rows.slice(2).map(cells)
      blocks.push(
        <div className="tw" key={i}><table><thead><tr>{head.map((c, k) => <th key={k}>{inline(c, onCite, `h${i}${k}`)}</th>)}</tr></thead>
          <tbody>{body.map((r, a) => <tr key={a}>{r.map((c, b) => <td key={b}>{inline(c, onCite, `t${i}${a}${b}`)}</td>)}</tr>)}</tbody></table></div>
      )
      i = j - 1
    } else if (/^\s*[-•*]\s+/.test(ln)) {
      const items = []
      let j = i
      while (j < lines.length && /^\s*[-•*]\s+/.test(lines[j])) { items.push(lines[j].replace(/^\s*[-•*]\s+/, '')); j++ }
      blocks.push(<ul key={i}>{items.map((t, k) => <li key={k}>{inline(t, onCite, `l${i}${k}`)}</li>)}</ul>)
      i = j - 1
    } else if (/^#{1,4}\s+/.test(ln)) {
      blocks.push(<h4 key={i}>{inline(ln.replace(/^#{1,4}\s+/, ''), onCite, `g${i}`)}</h4>)
    } else if (ln.trim()) {
      blocks.push(<p key={i}>{inline(ln, onCite, `p${i}`)}</p>)
    }
  }
  return <div className="md">{blocks}</div>
}

