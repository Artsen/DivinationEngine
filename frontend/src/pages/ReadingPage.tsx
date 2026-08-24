import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { collectionsApi, corpusStatusApi } from '../api/collections'
import { ApiError } from '../api/client'
import { readingsApi } from '../api/readings'
import { ErrorState, LoadingState } from '../components/AsyncState'
import { CastControls } from '../components/CastControls'
import { IChingCast } from '../components/IChingCast'
import { NotesPanel } from '../components/NotesPanel'
import { RuneCard } from '../components/RuneCard'
import { TarotCard } from '../components/TarotCard'
import { formatDate } from '../utils/format'

export function ReadingPage() {
  const { id = '' } = useParams()
  const reading = useQuery({ queryKey: ['reading', id], queryFn: () => readingsApi.context(id), enabled: Boolean(id) })
  const collections = useQuery({ queryKey: ['collections'], queryFn: collectionsApi.list })
  const corpus = useQuery({ queryKey: ['corpus-status'], queryFn: corpusStatusApi })
  if (reading.isPending) return <main className="page"><LoadingState>Opening reading…</LoadingState></main>
  if (reading.isError) return <main className="page"><ErrorState message={reading.error instanceof ApiError && reading.error.status === 404 ? 'This reading could not be found.' : 'Unable to load this reading.'} /><Link to="/readings">Return to readings</Link></main>
  const data = reading.data
  return (
    <main className="page reading-workspace">
      <Link className="back-link" to="/readings">← All readings</Link>
      <header className="reading-header">
        <div><p className="eyebrow">Reading · {formatDate(data.created_at)}</p><h1>{data.title}</h1>{data.question && <p className="reading-question">{data.question}</p>}</div>
        <span className="fact-notice">Stored facts · no generated interpretation</span>
      </header>
      <div className="workspace-grid">
        <div className="cast-history">
          <div className="section-heading"><div><p className="eyebrow">Persisted record</p><h2>Casts</h2></div><span>{data.casts.length}</span></div>
          {data.casts.length === 0 && <div className="empty-state empty-state--compact"><h3>No casts yet</h3><p>Choose Tarot, I Ching, or Runes to begin this reading.</p></div>}
          {data.casts.map((cast) => cast.cast_type === 'iching' ? (
            <IChingCast key={cast.id} cast={cast} sources={data.sources} traditions={data.traditions} />
          ) : (
            <article key={cast.id} className="cast-block">
              {cast.collection_id === collections.data?.find((row) => row.slug === 'elder-futhark')?.id ? <>
                <header className="cast-heading"><div><p className="eyebrow">Cast {cast.cast_order} · Runes</p><h3>{cast.draw_results.length} rune draw</h3></div><time dateTime={cast.created_at}>{formatDate(cast.created_at)}</time></header>
                <div className="rune-grid">{cast.draw_results.map((result) => <RuneCard key={result.id} result={result} sources={data.sources} traditions={data.traditions} />)}</div>
              </> : <>
                <header className="cast-heading"><div><p className="eyebrow">Cast {cast.cast_order} · Tarot</p><h3>{cast.draw_results.length} card draw</h3></div><time dateTime={cast.created_at}>{formatDate(cast.created_at)}</time></header>
                <div className="tarot-grid">{cast.draw_results.map((result) => <TarotCard key={result.id} result={result} sources={data.sources} traditions={data.traditions} />)}</div>
              </>}
            </article>
          ))}
        </div>
        <aside className="workspace-sidebar">
          {collections.isPending && <LoadingState>Loading cast options…</LoadingState>}
          {collections.isError && <ErrorState message="Unable to load corpus status." />}
          {collections.data && <CastControls readingId={id} collections={collections.data} casts={data.casts} ichingReady={corpus.data?.iching_ready ?? false} runesReady={corpus.data?.runes_ready ?? false} />}
          <NotesPanel readingId={id} notes={data.notes} />
        </aside>
      </div>
    </main>
  )
}
