import { imageUrl } from '../api/client'
import type {
  ContextDrawResult,
  ContextSource,
  ContextTradition,
} from '../api/types'
import { taxonomyLabel } from '../utils/format'
import { Provenance } from './Provenance'

interface Props {
  result: ContextDrawResult
  sources: Record<string, ContextSource>
  traditions: Record<string, ContextTradition>
}

export function TarotCard({ result, sources, traditions }: Props) {
  const name = result.item.display_name || result.item.name
  const orientation = result.orientation === 'reversed' ? 'reversed' : 'upright'
  return (
    <article className="tarot-card">
      <div className={`tarot-card__image-frame tarot-card__image-frame--${orientation}`}>
        <img src={imageUrl(result.item.id)} alt={`${name} — ${orientation}`} />
      </div>
      <header>
        <p className="eyebrow">Card {result.draw_order}</p>
        <h4>{name}</h4>
        <span className={`orientation orientation--${orientation}`}>{taxonomyLabel(orientation)}</span>
      </header>
      {result.placement && (
        <p className="placement">Placement: {result.placement.label || `(${result.placement.x}, ${result.placement.y})`}</p>
      )}
      <div className="knowledge-stack">
        {result.knowledge.applicable_interpretations.map((fact) => (
          <details key={fact.id} className="fact" open={fact.interpretation_type === orientation}>
            <summary>{taxonomyLabel(fact.interpretation_type)}</summary>
            <p className="source-text">{fact.exact_text}</p>
            <Provenance
              source={sources[fact.source_id]}
              tradition={fact.tradition_id ? traditions[fact.tradition_id] : undefined}
              locator={fact.locator}
            />
          </details>
        ))}
        {result.knowledge.other_interpretations.length > 0 && (
          <details className="fact">
            <summary>Other source text</summary>
            {result.knowledge.other_interpretations.map((fact) => (
              <section key={fact.id} className="nested-fact">
                <h5>{taxonomyLabel(fact.interpretation_type)}</h5>
                <p className="source-text">{fact.exact_text}</p>
                <Provenance
                  source={sources[fact.source_id]}
                  tradition={fact.tradition_id ? traditions[fact.tradition_id] : undefined}
                  locator={fact.locator}
                />
              </section>
            ))}
          </details>
        )}
        {result.knowledge.correspondences.length > 0 && (
          <details className="fact correspondence-group">
            <summary>Correspondences</summary>
            {result.knowledge.correspondences.map((fact) => (
              <section key={fact.id} className="nested-fact">
                <h5>{fact.tradition_id && traditions[fact.tradition_id] ? `${traditions[fact.tradition_id].name} · ` : ''}{taxonomyLabel(fact.type)}</h5>
                <p>{fact.value || 'No value recorded'} <span className="status-tag">{taxonomyLabel(fact.status)}</span></p>
                <Provenance
                  source={sources[fact.source_id]}
                  tradition={fact.tradition_id ? traditions[fact.tradition_id] : undefined}
                  locator={fact.locator}
                />
              </section>
            ))}
          </details>
        )}
      </div>
    </article>
  )
}
