import type { ContextSource, ContextTradition, Hexagram, IChingText } from '../api/types'
import { taxonomyLabel } from '../utils/format'
import { HexagramDiagram } from './HexagramDiagram'
import { Provenance } from './Provenance'

interface Props {
  label: string
  hexagram: Hexagram
  changingLines?: number[]
  values?: Record<number, number>
  sources: Record<string, ContextSource>
  traditions: Record<string, ContextTradition>
}

function TextFact({ text, sources, traditions }: {
  text: IChingText
  sources: Record<string, ContextSource>
  traditions: Record<string, ContextTradition>
}) {
  return (
    <section className={`iching-text iching-text--${text.language}`}>
      <h5>{taxonomyLabel(text.unit_type)}{text.line_position ? ` · Line ${text.line_position}` : ''}</h5>
      <p lang={text.language === 'zh-Hant' ? 'zh-Hant' : 'en'}>{text.exact_text}</p>
      <Provenance
        source={sources[text.source_id]}
        tradition={text.tradition_id ? traditions[text.tradition_id] : undefined}
        locator={text.locator}
      />
    </section>
  )
}

export function HexagramPanel({ label, hexagram, changingLines = [], values, sources, traditions }: Props) {
  const primaryTexts = hexagram.texts.filter((text) => text.unit_type !== 'tuan')
  const tuan = hexagram.texts.filter((text) => text.unit_type === 'tuan')
  return (
    <article className="hexagram-panel">
      <p className="eyebrow">{label}</p>
      <header className="hexagram-title">
        <span className="hexagram-glyph" aria-hidden="true">{hexagram.glyph}</span>
        <div>
          <h4>{hexagram.canonical_number}. <span lang="zh-Hant">{hexagram.chinese_name}</span></h4>
          <p>{hexagram.pinyin} · {hexagram.legge_title}</p>
        </div>
      </header>
      <HexagramDiagram pattern={hexagram.binary_pattern} changingLines={changingLines} values={values} />
      <div className="iching-texts">
        {primaryTexts.map((text) => <TextFact key={text.key} text={text} sources={sources} traditions={traditions} />)}
        {tuan.length > 0 && (
          <details className="fact">
            <summary>Tuan commentary</summary>
            {tuan.map((text) => <TextFact key={text.key} text={text} sources={sources} traditions={traditions} />)}
          </details>
        )}
      </div>
    </article>
  )
}
