import type { Collection, ContextCast, ContextSource, ContextTradition } from '../api/types'
import { formatDate } from '../utils/format'
import { IChingCast } from './IChingCast'
import { RuneCard } from './RuneCard'
import { TarotCard } from './TarotCard'

interface Props {
  casts: ContextCast[]
  collections: Collection[]
  sources: Record<string, ContextSource>
  traditions: Record<string, ContextTradition>
}

export function CastTimeline({ casts, collections, sources, traditions }: Props) {
  const runeCollection = collections.find((row) => row.slug === 'elder-futhark')
  const latestOrder = Math.max(0, ...casts.map((cast) => cast.cast_order))
  return <div className="cast-timeline">{casts.map((cast) => {
    const isLatest = cast.cast_order === latestOrder
    if (cast.cast_type === 'iching') {
      return <IChingCast key={cast.id} cast={cast} sources={sources} traditions={traditions} latest={isLatest} />
    }
    const runes = cast.collection_id === runeCollection?.id
    const count = cast.draw_results.length
    return <article key={cast.id} className={`cast-block${isLatest ? ' cast-block--latest' : ''}`}>
      <header className="cast-heading"><div>
        <p className="eyebrow">Cast {cast.cast_order}{isLatest ? ' · Latest' : ''}</p>
        <h3>{runes ? 'Rune draw' : 'Tarot draw'}</h3>
        <p className="cast-meta">{count} {runes ? `rune${count === 1 ? '' : 's'}` : `card${count === 1 ? '' : 's'}`} · {cast.spread?.name ?? 'Unstructured draw'} · {runes ? 'Finite bag' : 'Rider–Waite–Smith'}{cast.configuration.reversals_enabled ? ' · Reversals allowed' : ''}</p>
        {runes && cast.spread && <p className="layout-disclaimer">Modern editorial layout; not evidence of an ancient Germanic casting method.</p>}
      </div><time dateTime={cast.created_at}>{formatDate(cast.created_at)}</time></header>
      <div className={`${runes ? 'rune-grid' : 'tarot-grid'}${cast.spread ? ' spread-result-layout' : ''}`}>
        {cast.draw_results.map((result) => runes
          ? <RuneCard key={result.id} result={result} sources={sources} traditions={traditions} />
          : <TarotCard key={result.id} result={result} sources={sources} traditions={traditions} />)}
      </div>
    </article>
  })}</div>
}
