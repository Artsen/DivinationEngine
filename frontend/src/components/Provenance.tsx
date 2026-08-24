import type { ContextSource, ContextTradition } from '../api/types'

interface Props {
  source?: ContextSource
  tradition?: ContextTradition
  locator?: string | null
}

export function Provenance({ source, tradition, locator }: Props) {
  if (!source && !tradition && !locator) return null
  return (
    <details className="provenance">
      <summary>Provenance</summary>
      <dl>
        {source && <><dt>Source</dt><dd>{source.title}</dd></>}
        {source?.author && <><dt>Author / translator</dt><dd>{source.author}</dd></>}
        {source?.edition && <><dt>Edition</dt><dd>{source.edition}</dd></>}
        {source?.publisher && <><dt>Publisher</dt><dd>{source.publisher}</dd></>}
        {source?.publication_year && <><dt>Year</dt><dd>{source.publication_year}</dd></>}
        {tradition && <><dt>Tradition / layer</dt><dd>{tradition.name}</dd></>}
        {locator && <><dt>Locator</dt><dd>{locator}</dd></>}
        {source?.rights_status && <><dt>Rights</dt><dd>{source.rights_status.replaceAll('_', ' ')}</dd></>}
      </dl>
      {source?.source_url && <a href={source.source_url} target="_blank" rel="noreferrer">Open source record</a>}
    </details>
  )
}
