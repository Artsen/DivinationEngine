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
  const waiteFacts = result.knowledge.applicable_interpretations.filter((fact) => {
    const source = sources[fact.source_id]
    return fact.interpretation_type === orientation && (source?.author?.includes('Waite') || source?.title.includes('Pictorial Key'))
  })
  const secondaryFacts = result.knowledge.applicable_interpretations.filter((fact) => !waiteFacts.includes(fact))
  return (
    <article className="tarot-card">
      {result.placement?.position_label && <header className="placement-heading"><p className="eyebrow">Position {result.placement.sequence}</p><h4>{result.placement.position_label}</h4>{result.placement.position_description && <p>{result.placement.position_description}</p>}</header>}
      <div className={`tarot-card__image-frame tarot-card__image-frame--${orientation}`}>
        <img src={imageUrl(result.item.id)} alt={`${name} — ${orientation}`} />
      </div>
      <header>
        <p className="eyebrow">Card {result.draw_order}</p>
        <h4>{name}</h4>
        <span className={`orientation orientation--${orientation}`}>{taxonomyLabel(orientation)}</span>
      </header>
      <div className="knowledge-stack">
        {waiteFacts.length > 0 && <section className="primary-meaning" aria-label="Primary Waite text"><p className="meaning-label">Waite · {taxonomyLabel(orientation)}</p>{waiteFacts.map((fact) => <div key={fact.id} className="primary-meaning__text"><p className="source-text">{fact.exact_text}</p>{fact.locator && <small>{fact.locator}</small>}</div>)}<details className="provenance-disclosure"><summary>Source</summary><Provenance source={sources[waiteFacts[0].source_id]} tradition={waiteFacts[0].tradition_id ? traditions[waiteFacts[0].tradition_id] : undefined} /></details></section>}
        {secondaryFacts.length > 0 && <details className="fact"><summary>Symbolism and description</summary>{secondaryFacts.map((fact) => <section key={fact.id} className="nested-fact"><h5>{taxonomyLabel(fact.interpretation_type)}</h5><p className="source-text">{fact.exact_text}</p><Provenance source={sources[fact.source_id]} tradition={fact.tradition_id ? traditions[fact.tradition_id] : undefined} locator={fact.locator} /></section>)}</details>}
        {result.knowledge.other_interpretations.length > 0 && (
          <details className="fact">
            <summary>Other source traditions</summary>
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
            <summary>Tradition-specific correspondences</summary>
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
