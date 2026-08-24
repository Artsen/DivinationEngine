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
  system?: string
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

function systemName(slug: string): string {
  return slug.split('-').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
}

function systemAbbreviation(name: string): string {
  const words = name.split(/\s+/).filter(Boolean)
  return words.length === 1
    ? words[0].slice(0, 2).toUpperCase()
    : `${words[0][0]}${words.at(-1)?.[0]}`.toUpperCase()
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
  const canonicalSystemName = systemName(metadata.system || 'runes')
  const relatedSystems = Array.from(
    poems.reduce((systems, poem) => {
      const tradition = traditions[poem.tradition_id]
      if (!tradition) return systems
      const current = systems.get(tradition.id)
      systems.set(tradition.id, {
        id: tradition.id,
        name: tradition.name,
        cautious: (current?.cautious ?? false) || poem.mapping_status !== 'direct',
      })
      return systems
    }, new Map<string, { id: string; name: string; cautious: boolean }>()),
  ).map(([, system]) => system)

  return (
    <article className="rune-card">
      <header className="rune-card__identity">
        <span className="rune-glyph" aria-hidden="true">{result.item.symbol}</span>
        <div>
          <p className="eyebrow">Rune {result.draw_order} · {canonicalSystemName} #{metadata.row_position}</p>
          <h4>{result.item.name}</h4>
          <p className="rune-transliteration">Transliteration {metadata.transliteration}</p>
        </div>
      </header>
      <details className="tradition-connections fact">
        <summary>Related historical systems</summary>
        <section aria-label="Tradition connections">
        <h5>Tradition connections</h5>
        <ul className="tradition-chips">
          <li className="tradition-chip tradition-chip--core">
            <span className="tradition-chip__mark" aria-hidden="true">{systemAbbreviation(canonicalSystemName)}</span>
            <span><strong>{canonicalSystemName}</strong><small>Core system</small></span>
          </li>
          {relatedSystems.map((system) => <li key={system.id} className={`tradition-chip${system.cautious ? ' tradition-chip--cautious' : ''}`}>
            <span className="tradition-chip__mark" aria-hidden="true">{systemAbbreviation(system.name)}</span>
            <span><strong>{system.name}</strong><small>{system.cautious ? 'Related system · cautious relationship' : 'Related historical system'}</small></span>
          </li>)}
        </ul>
        </section>
      </details>
      <dl className="rune-facts">
        <dt>Reconstructed name</dt>
        <dd>{metadata.proto_germanic_name} <span className="status-tag">{taxonomyLabel(metadata.reconstruction_status || 'unknown')}</span></dd>
        <dt>Lexical reconstruction</dt><dd>{metadata.lexical_reconstruction || 'Unknown'}</dd>
        <dt>Sound value</dt><dd>{metadata.sound_value || 'Unknown'}</dd>
        <dt>Position</dt><dd>Row {metadata.row_position} · Ætt {metadata.aett}, position {metadata.position_in_aett}</dd>
      </dl>
      {metadata.uncertainty_notes && <p className="rune-caution"><strong>Evidence caution:</strong> {metadata.uncertainty_notes}</p>}
      <div className="knowledge-stack">
        <details className="fact">
          <summary>Historical evidence</summary>
          <p className="muted">Canonical identity is separated from later poems and modern divination. Archaeological row records and limitations are documented in the corpus source registry.</p>
          {historicalEvidence.map((fact) => <section key={fact.id} className="nested-fact"><h5>{taxonomyLabel(fact.type)}</h5><p>{fact.value} <span className="status-tag">{taxonomyLabel(fact.status)}</span></p>{fact.notes && <p className="rune-caution">{fact.notes}</p>}<Provenance source={sources[fact.source_id]} tradition={fact.tradition_id ? traditions[fact.tradition_id] : undefined} locator={fact.locator} /></section>)}
        </details>
        <details className="fact">
          <summary>Rune poems</summary>
          {poems.map((poem) => {
            const tradition = traditions[poem.tradition_id]
            const label = poemLabels[poem.poem] || taxonomyLabel(poem.poem)
            const cautious = poem.mapping_status !== 'direct'
            return <details key={poem.id} className="poem-witness" open={poems.length === 1}>
              <summary>
                <strong>{label} Rune Poem</strong>
                <span>{tradition?.name} · {poem.normalized_name}{cautious && ' · Related with caution'}</span>
              </summary>
              <div className="poem-witness__body">
                <p className="poem-layer-label">Modern English</p>
                <p className="translation-text">{poem.editorial_translation}</p>
                {poem.editorial_latin_gloss && <p><strong>Latin tag, translated:</strong> {poem.editorial_latin_gloss}</p>}
                <p className="translation-notice">DivinationEngine editorial translation · modern, derived, machine-assisted. It is not historical source text or divinatory meaning.</p>
                <p className="poem-layer-label">Historical original · {languageLabels[poem.language] || taxonomyLabel(poem.language)}</p>
                <p className="source-text">{poem.original_text}</p>
                {poem.latin_tag && <p className="source-text"><strong>Historical Latin tag:</strong> {poem.latin_tag}</p>}
                {poem.translation_notes && <p className="rune-caution"><strong>Translation note:</strong> {poem.translation_notes}</p>}
                {cautious && <p className="rune-caution"><strong>Cautious mapping:</strong> {poem.mapping_justification}</p>}
                <Provenance source={sources[poem.source_id]} tradition={tradition} locator={poem.locator} />
                <details className="translation-sources">
                  <summary>Translation references</summary>
                  {poem.translation_source_ids.map((sourceId) => {
                    const source = sources[sourceId]
                    return source && <Provenance key={sourceId} source={source} />
                  })}
                </details>
              </div>
            </details>
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
