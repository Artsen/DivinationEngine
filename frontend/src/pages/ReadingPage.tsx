import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { collectionsApi, corpusStatusApi } from '../api/collections'
import { ApiError } from '../api/client'
import { readingsApi } from '../api/readings'
import { spreadsApi } from '../api/spreads'
import { AddCastFlow } from '../components/AddCastFlow'
import { ErrorState, LoadingState } from '../components/AsyncState'
import { CastTimeline } from '../components/CastTimeline'
import { NotesPanel } from '../components/NotesPanel'
import { formatDate } from '../utils/format'

export function ReadingPage() {
  const { id = '' } = useParams()
  const reading = useQuery({ queryKey: ['reading', id], queryFn: () => readingsApi.context(id), enabled: Boolean(id) })
  const collections = useQuery({ queryKey: ['collections'], queryFn: collectionsApi.list })
  const corpus = useQuery({ queryKey: ['corpus-status'], queryFn: corpusStatusApi })
  const spreads = useQuery({ queryKey: ['spreads'], queryFn: spreadsApi.list })
  if (reading.isPending) return <main className="page"><LoadingState>Opening reading…</LoadingState></main>
  if (reading.isError) return <main className="page"><ErrorState message={reading.error instanceof ApiError && reading.error.status === 404 ? 'This reading could not be found.' : 'Unable to load this reading.'} /><Link to="/readings">Return to readings</Link></main>
  const data = reading.data
  return <main className="page reading-workspace">
    <Link className="back-link" to="/readings">← All readings</Link>
    <header className="reading-header">
      <div><p className="eyebrow">Reading · {formatDate(data.created_at)}</p><h1>{data.title}</h1>{data.question && <p className="reading-question">{data.question}</p>}</div>
      <span className="fact-notice">Stored facts · no generated interpretation</span>
    </header>
    <div className="reading-flow">
      <section className="cast-history" aria-labelledby="casts-heading">
        <div className="section-heading"><div><p className="eyebrow">Your cast record</p><h2 id="casts-heading">Casts</h2></div><span>{data.casts.length}</span></div>
        {data.casts.length === 0 && <div className="guided-empty"><p className="eyebrow">Begin here</p><h3>This reading is ready for its first cast.</h3><p>Choose a system below. You will confirm its method and options before anything is drawn.</p></div>}
        {collections.data && <CastTimeline casts={data.casts} collections={collections.data} sources={data.sources} traditions={data.traditions} />}
        {collections.isPending && <LoadingState>Loading cast options…</LoadingState>}
        {collections.isError && <ErrorState message="Unable to load corpus status." />}
        {collections.data && <AddCastFlow readingId={id} collections={collections.data} casts={data.casts} spreads={spreads.data ?? []} ichingReady={corpus.data?.iching_ready ?? false} runesReady={corpus.data?.runes_ready ?? false} />}
      </section>
      <NotesPanel readingId={id} notes={data.notes} />
    </div>
  </main>
}
