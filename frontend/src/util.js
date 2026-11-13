// Paleta de gráficos (estilo Power BI)
export const PAL = ['#01B8AA', '#F2C811', '#FD625E', '#8AD4EB', '#FE9666', '#A66999', '#3599B8', '#374649']
export const PERSP = {
  prazos: { nome: 'Prazos', cor: '#01B8AA' },
  valores: { nome: 'Valores', cor: '#F2C811' },
  obrigacoes: { nome: 'Obrigações', cor: '#8AD4EB' },
  riscos: { nome: 'Riscos', cor: '#FD625E' },
}

export const fmtData = (d) => (d ? new Date(d + 'T00:00:00').toLocaleDateString('pt-BR') : '—')
export const iniciais = (n = '') => n.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase()

// Mescla trechos consecutivos removendo a sobreposição (mesma regra do backend)
export function mergeChunks(parts) {
  if (!parts.length) return ''
  let out = parts[0]
  for (const nxt of parts.slice(1)) {
    let k = Math.min(out.length, nxt.length, 400)
    while (k >= 15 && !out.endsWith(nxt.slice(0, k))) k--
    out += k >= 15 ? nxt.slice(k) : '\n' + nxt
  }
  return out
}

// Quebra de texto em linhas para rótulos SVG
export function wrap(text, max) {
  const words = String(text).split(/\s+/); const lines = []; let cur = ''
  for (const w of words) {
    if ((cur + ' ' + w).trim().length > max && cur) { lines.push(cur); cur = w } else cur = (cur + ' ' + w).trim()
  }
  if (cur) lines.push(cur)
  return lines
}

export const perspDados = (g) => Object.entries(PERSP).map(([k, v]) => ({ k, ...v, n: g.por_perspectiva[k] || 0 }))

export const CLASSIF = {
  publica: { nome: 'Pública', nivel: 0 }, interna: { nome: 'Interna', nivel: 1 },
  restrita: { nome: 'Restrita', nivel: 2 }, confidencial: { nome: 'Confidencial', nivel: 3 },
}
