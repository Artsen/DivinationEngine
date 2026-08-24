import type { ContextCast, ContextSource, ContextTradition } from '../api/types'
import { formatDate, taxonomyLabel } from '../utils/format'
import { HexagramPanel } from './HexagramPanel'

interface Props {
  cast: ContextCast
  sources: Record<string, ContextSource>
  traditions: Record<string, ContextTradition>
}

export function IChingCast({ cast, sources, traditions }: Props) {
  const iching = cast.iching
  const knowledge = iching?.knowledge
  const primary = knowledge?.primary
  if (!iching || !knowledge || !primary) return null
  const { throws, method } = iching
  const values = Object.fromEntries(throws.map((row) => [row.line_number, row.line_value]))
  const hasChanges = knowledge.changing_lines.length > 0
  return (
    <article className="cast-block">
      <header className="cast-heading">
        <div><p className="eyebrow">Cast {cast.cast_order} · I Ching</p><h3>{taxonomyLabel(method)}</h3></div>
        <time dateTime={cast.created_at}>{formatDate(cast.created_at)}</time>
      </header>
      <div className={`hexagram-pair ${hasChanges ? 'has-relating' : ''}`}>
        <HexagramPanel
          label="Primary hexagram"
          hexagram={primary}
          changingLines={knowledge.changing_lines}
          values={values}
          sources={sources}
          traditions={traditions}
        />
        {hasChanges && knowledge.relating && <div className="relating-arrow" aria-label="relates to">→</div>}
        {hasChanges && knowledge.relating && (
          <HexagramPanel label="Relating hexagram" hexagram={knowledge.relating} sources={sources} traditions={traditions} />
        )}
      </div>
      {!hasChanges && <p className="no-changes">There are no changing lines in this cast.</p>}
      <p className="selection-notice">{knowledge.selection_notice}</p>
      <details className="casting-details">
        <summary>Casting details</summary>
        <p>Method: {taxonomyLabel(method)}. Stored order: bottom to top.</p>
        <ol>
          {throws.map((row) => (
            <li key={row.line_number}>
              Line {row.line_number}: value {row.line_value}
              {row.coins && ` · coins ${row.coins.join(' + ')}`}
              {row.procedure && <details><summary>Manipulation trace</summary><pre>{JSON.stringify(row.procedure, null, 2)}</pre></details>}
            </li>
          ))}
        </ol>
      </details>
    </article>
  )
}
