// Layout em camadas para fluxogramas com decisões e retornos (laços).
// - arestas de retorno (que voltam a uma etapa anterior) são separadas e desenhadas por fora;
// - o caminho principal fica numa coluna e as alternativas de uma decisão abrem colunas ao lado.
export const NW = 236, NH = 58, GX = 56, GY = 46

export function layoutFlow(nos, arestas) {
  const out = {}, inn = {}
  nos.forEach((n) => { out[n.id] = []; inn[n.id] = [] })
  arestas.forEach((e) => { if (out[e.de] && inn[e.para]) out[e.de].push(e) })

  // 1) separa arestas de retorno por DFS
  const state = {}, back = new Set(), order = []
  const dfs = (u) => {
    state[u] = 1
    for (const e of out[u]) {
      if (state[e.para] === 1) back.add(e)
      else if (!state[e.para]) dfs(e.para)
    }
    state[u] = 2; order.push(u)
  }
  const starts = nos.filter((n) => !arestas.some((e) => e.para === n.id)).map((n) => n.id)
  ;(starts.length ? starts : [nos[0]?.id]).forEach((s) => s && !state[s] && dfs(s))
  nos.forEach((n) => !state[n.id] && dfs(n.id))
  const fwd = arestas.filter((e) => !back.has(e) && out[e.de])
  fwd.forEach((e) => inn[e.para].push(e))

  // 2) camada = caminho mais longo a partir do início
  const layer = {}
  ;[...order].reverse().forEach((u) => {
    layer[u] = Math.max(0, ...inn[u].map((e) => layer[e.de] + 1))
  })

  // 3) colunas: cada nó herda a coluna do predecessor; irmãos (saídas de uma decisão) abrem colunas à direita
  const col = {}
  const byLayer = {}
  nos.forEach((n) => { (byLayer[layer[n.id]] ||= []).push(n.id) })
  Object.keys(byLayer).map(Number).sort((a, b) => a - b).forEach((L) => {
    const taken = new Set()
    byLayer[L].forEach((id) => {
      const preds = inn[id]
      let c = preds.length ? Math.min(...preds.map((e) => col[e.de] ?? 0)) : 0
      const p = preds[0] && fwd.filter((e) => e.de === preds[0].de)
      if (p && p.length > 1) { // saída alternativa de decisão
        const idx = p.findIndex((e) => e.para === id)
        const base = col[preds[0].de] ?? 0
        if (idx > 0 && preds.length === 1) c = base + idx
      }
      while (taken.has(c)) c++
      taken.add(c); col[id] = c
    })
  })

  const hasBack = back.size > 0
  const padL = hasBack ? 210 : 24
  const maxCol = Math.max(0, ...Object.values(col))
  const maxLayer = Math.max(0, ...Object.values(layer))
  const pos = {}
  nos.forEach((n) => { pos[n.id] = { x: padL + col[n.id] * (NW + GX), y: 24 + layer[n.id] * (NH + GY) } })
  return {
    pos, back, fwd,
    width: padL + (maxCol + 1) * (NW + GX) + 8,
    height: 24 + (maxLayer + 1) * (NH + GY),
  }
}
