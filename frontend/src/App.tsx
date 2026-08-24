import { useQuery } from '@tanstack/react-query'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { corpusStatusApi, healthApi } from './api/collections'

export function App() {
  const health = useQuery({ queryKey: ['health'], queryFn: healthApi, retry: 1, refetchInterval: 30_000 })
  const corpus = useQuery({ queryKey: ['corpus-status'], queryFn: corpusStatusApi, enabled: health.isSuccess })
  if (health.isError) {
    return (
      <main className="offline-page">
        <div className="brand-mark" aria-hidden="true">DE</div>
        <p className="eyebrow">Connection</p><h1>DivinationEngine API is unavailable.</h1>
        <p>Start the backend with <code>uvicorn app.main:app --app-dir backend --reload</code>, then try again.</p>
        <button type="button" onClick={() => health.refetch()}>Try again</button>
      </main>
    )
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <Link to="/" className="brand"><span className="brand-mark" aria-hidden="true">DE</span><span>DivinationEngine<small>Source-backed readings</small></span></Link>
        <nav aria-label="Primary">{corpus.data?.rws_ready && corpus.data.iching_ready && <span className="system-ready" title="API, database, RWS, and I Ching corpora are ready">Ready</span>}<NavLink to="/readings">Readings</NavLink><NavLink className="new-reading-link" to="/readings/new">New reading</NavLink></nav>
      </header>
      {health.isPending ? <div className="health-line" role="status">Connecting to the API…</div> : <>
        {corpus.data && (!corpus.data.rws_ready || !corpus.data.iching_ready) && <div className="setup-banner" role="status"><strong>Corpus setup is incomplete.</strong> Run <code>divination-dev-bootstrap</code> in the backend terminal.</div>}
        <Outlet />
      </>}
      <footer className="site-footer"><p>Mechanical casts. Historical sources. Your interpretation.</p><a href="/docs" target="_blank" rel="noreferrer">API documentation</a></footer>
    </div>
  )
}
