import { createContext, useContext, useEffect, useState } from 'react'

export const AppCtx = createContext(null)
export const useApp = () => useContext(AppCtx)

// Roteamento por hash: #/documentos/rh?q=ferias
export function useRoute() {
  const parse = () => {
    const raw = window.location.hash.replace(/^#\/?/, '')
    const [path, qs = ''] = raw.split('?')
    return { parts: path.split('/').filter(Boolean), q: new URLSearchParams(qs) }
  }
  const [route, setRoute] = useState(parse)
  useEffect(() => {
    const on = () => { setRoute(parse()); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return route
}
export const go = (path) => { window.location.hash = '/' + path.replace(/^\/+/, '') }

export function useAsync(fn, deps) {
  const key = JSON.stringify(deps)
  const [state, setState] = useState({ key: null, data: null, error: null })
  useEffect(() => {
    let alive = true
    fn().then((data) => alive && setState({ key, data, error: null }))
      .catch((error) => alive && setState({ key, data: null, error }))
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  const ready = state.key === key
  return { loading: !ready, data: ready ? state.data : null, error: ready ? state.error : null }
}
