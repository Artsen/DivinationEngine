import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { readingsApi } from '../api/readings'
import { ErrorState, LoadingState } from '../components/AsyncState'
import { castTypeLabel, formatDate } from '../utils/format'

export function ReadingsPage() {
  const query = useQuery({ queryKey: ['readings'], queryFn: readingsApi.list })
  return (
    <main className="page page--readings">
      <section className="hero">
        <div><p className="eyebrow">Your private reading record</p><h1>Read what was drawn.<br />Keep what matters.</h1><p>Mechanical casts, historical sources, and your own notes—kept distinct.</p></div>
        <Link className="button-primary" to="/readings/new">New reading</Link>
      </section>
      <section aria-labelledby="recent-heading">
        <div className="section-heading"><div><p className="eyebrow">History</p><h2 id="recent-heading">Recent readings</h2></div></div>
        {query.isPending && <LoadingState>Loading readings…</LoadingState>}
        {query.isError && <ErrorState message="Unable to load readings." />}
        {query.data?.length === 0 && <div className="empty-state"><span aria-hidden="true">☰</span><h3>No readings yet</h3><p>Begin with a question, then draw Tarot or cast the I Ching.</p><Link to="/readings/new">Start a reading</Link></div>}
        {query.data && query.data.length > 0 && <div className="reading-grid">{query.data.map((reading) => <Link key={reading.id} to={`/readings/${reading.id}`} className="reading-card"><div><p className="eyebrow">{formatDate(reading.created_at)}</p><h3>{reading.title}</h3><p>{reading.question || 'No question recorded'}</p></div><footer><span>{reading.cast_count} {reading.cast_count === 1 ? 'cast' : 'casts'}</span><span>{reading.cast_types.map(castTypeLabel).join(' · ') || 'Open reading'}</span><span aria-hidden="true">→</span></footer></Link>)}</div>}
      </section>
    </main>
  )
}
