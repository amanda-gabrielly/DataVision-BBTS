// Cliente da API. Todos os dados vêm do FastAPI/PostgreSQL; nada é fixo no front.
// Sessão: o token do login vai no cabeçalho Authorization (em produção: SSO/AD do BBTS).
export const getToken = () => { try { return localStorage.getItem('dv-token') || '' } catch { return '' } }
export const setToken = (t) => { try { t ? localStorage.setItem('dv-token', t) : localStorage.removeItem('dv-token') } catch { /* sem storage */ } }

async function req(path, opts = {}) {
  const token = getToken()
  const res = await fetch('/api' + path, token ? { ...opts, headers: { ...opts.headers, Authorization: 'Bearer ' + token } } : opts)
  let body = null
  try { body = await res.json() } catch { /* corpo vazio */ }
  if (res.status === 401 && token && path !== '/login') {  // sessão expirada: volta para o login
    setToken(''); window.dispatchEvent(new Event('dv-logout'))
  }
  if (!res.ok) {
    const msg = typeof body?.detail === 'string' ? body.detail : 'Não foi possível concluir a ação.'
    throw Object.assign(new Error(msg), { status: res.status })
  }
  return body
}
const json = (method, data) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })

export const api = {
  health: () => req('/health'),
  painel: () => req('/painel'),
  pastas: () => req('/pastas'),
  documentos: (p = {}) => {
    const q = new URLSearchParams(Object.entries(p).filter(([, v]) => v)).toString()
    return req('/documentos' + (q ? '?' + q : ''))
  },
  documento: (id) => req(`/documentos/${id}`),
  visoes: (id, versaoId) => req(`/documentos/${id}/visoes` + (versaoId ? `?versao_id=${versaoId}` : '')),
  trechos: (id, versaoId, pagina) =>
    req(`/documentos/${id}/trechos?` + new URLSearchParams({ ...(versaoId && { versao_id: versaoId }), ...(pagina && { pagina }) })),
  resumo: (id, perspectiva, versaoId) =>
    req(`/documentos/${id}/resumo?` + new URLSearchParams({ perspectiva, ...(versaoId && { versao_id: versaoId }) })),
  enviar: (file, pasta, classificacao) => {
    const f = new FormData(); f.append('file', file); if (pasta) f.append('pasta', pasta)
    if (classificacao) f.append('classificacao', classificacao)
    return req('/documentos', { method: 'POST', body: f })
  },
  salvar: (id) => req(`/documentos/${id}/salvo`, { method: 'PUT' }),
  removerSalvo: (id) => req(`/documentos/${id}/salvo`, { method: 'DELETE' }),
  perguntar: (data) => req('/perguntar', json('POST', data)),
  consultas: () => req('/consultas'),
  me: () => req('/me'),
  config: () => req('/config'),
  contasDemo: () => req('/usuarios'),
  login: (email, senha) => req('/login', json('POST', { email, senha })),
  logout: () => req('/logout', { method: 'POST' }),
  trocarSenha: (atual, nova) => req('/me/senha', json('PUT', { atual, nova })),
  reclassificar: (id, classificacao) => req(`/documentos/${id}/classificacao`, json('PUT', { classificacao })),
  atualizarMe: (data) => req('/me', json('PUT', data)),
}
