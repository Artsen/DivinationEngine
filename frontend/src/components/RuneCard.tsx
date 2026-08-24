import type { ContextDrawResult, ContextSource, ContextTradition } from '../api/types'
import { taxonomyLabel } from '../utils/format'
import { Provenance } from './Provenance'

interface Props {
  result: ContextDrawResult
  sources: Record<string, ContextSource>
  traditions: Record<string, ContextTradition>
}

interface RuneMetadata {
  row_position?: number
  aett?: number
  position_in_aett?: number
  transliteration?: string
  sound_value?: string
  proto_germanic_name?: string
  reconstruction_status?: string
  lexical_reconstruction?: string
  uncertainty_notes?: string | null
}

const poemLabels: Record<string, string> = {
  'old-english': 'Old English',
  norwegian: 'Norwegian',
  icelandic: 'Icelandic',
}

const languageLabels: Record<string, string> = {
  ang: 'Old English',
  non: 'Old Norse',
}

export function RuneCard({ result, sources, traditions }: Props) {
  const metadata = result.item.metadata as RuneMetadata
  const poems = result.knowledge.rune_poems ?? []
  const reconstruction = result.knowledge.correspondences.filter((fact) =>
    ['reconstructed_name', 'lexical_reconstruction', 'historical_sound_value'].includes(fact.type),
  )
  const historicalEvidence = result.knowledge.correspondences.filter(
    (fact) => ['unicode_identity', 'archaeological_attestation'].includes(fact.type),
  )

  return (
    <article className="rune-card">
      <header className="rune-card__identity">
        <span className="rune-glyph" aria-hidden="true">{result.item.symbol}</span>
        <div>
          <p className="eyebrow">Rune {result.draw_order} · Elder Futhark #{metadata.row_position}</p>
          <h4>{result.item.name}</h4>
          <p className="rune-transliteration">Transliteration {metadata.transliteration}</p>
        </div>
      </header>
      <dl className="rune-facts">
        <dt>Reconstructed name</dt>
        <dd>{metadata.proto_germanic_name} <span className="status-tag">{taxonomyLabel(metadata.reconstruction_status || 'unknown')}</span></dd>
        <dt>Lexical reconstruction</dt><dd>{metadata.lexical_reconstruction || 'Unknown'}</dd>
        <dt>Sound value</dt><dd>{metadata.sound_value || 'Unknown'}</dd>
        <dt>Group</dt><dd>Ætt {metadata.aett}, position {metadata.position_in_aett}</dd>
      </dl>
      {metadata.uncertainty_notes && <p className="rune-caution"><strong>Evidence caution:</strong> {metadata.uncertainty_notes}</p>}
      <div className="knowledge-stack">
        <details className="fact">
          <summary>Historical evidence</summary>
          <p className="muted">Canonical identity is separated from later poems and modern divination. Archaeological row records and limitations are documented in the corpus source registry.</p>
          {historicalEvidence.map((fact) => <section key={fact.id} className="nested-fact"><h5>{taxonomyLabel(fact.type)}</h5><p>{fact.value} <span className="status-tag">{taxonomyLabel(fact.status)}</span></p>{fact.notes && <p className="rune-caution">{fact.notes}</p>}<Provenance source={sources[fact.source_id]} tradition={fact.tradition_id ? traditions[fact.tradition_id] : undefined} locator={fact.locator} /></section>)}
        </details>
        <details className="fact" open>
          <summary>Rune poems</summary>
          {poems.map((poem) => {
            const tradition = traditions[poem.tradition_id]
            return <section key={poem.id} className="nested-fact rune-poem">
              <h5>{poemLabels[poem.poem] || taxonomyLabel(poem.poem)} · {tradition?.name}</h5>
              <p className="poem-layer-label">Modern English</p>
              <p className="translation-text">{poem.editorial_translation}</p>
              {poem.editorial_latin_gloss && <p><strong>Latin tag, translated:</strong> {poem.editorial_latin_gloss}</p>}
              <p className="translation-notice">DivinationEngine editorial translation · modern, derived, machine-assisted. It is not historical source text or divinatory meaning.</p>
              {poem.translation_notes && <p className="rune-caution"><strong>Translation note:</strong> {poem.translation_notes}</p>}
              <p className="poem-layer-label">Historical original · {languageLabels[poem.language] || taxonomyLabel(poem.language)}</p>
              <p className="source-text">{poem.original_text}</p>
              {poem.latin_tag && <p className="source-text"><strong>Historical Latin tag:</strong> {poem.latin_tag}</p>}
              {poem.mapping_status !== 'direct' && <p className="rune-caution"><strong>Cautious mapping:</strong> {poem.mapping_justification}</p>}
              <Provenance source={sources[poem.source_id]} tradition={tradition} locator={poem.locator} />
              <details className="translation-sources">
                <summary>Translation references</summary>
                {poem.translation_source_ids.map((sourceId) => {
                  const source = sources[sourceId]
                  return source && <Provenance key={sourceId} source={source} />
                })}
              </details>
            </section>
          })}
        </details>
        <details className="fact">
          <summary>Reconstruction</summary>
          {reconstruction.map((fact) => <section key={fact.id} className="nested-fact"><h5>{taxonomyLabel(fact.type)}</h5><p>{fact.value} <span className="status-tag">{taxonomyLabel(fact.status)}</span></p><Provenance source={sources[fact.source_id]} tradition={fact.tradition_id ? traditions[fact.tradition_id] : undefined} locator={fact.locator} /></section>)}
        </details>
      </div>
    </article>
  )
}
