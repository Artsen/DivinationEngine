interface Props {
  pattern: string
  changingLines?: number[]
  values?: Record<number, number>
}

export function HexagramDiagram({ pattern, changingLines = [], values = {} }: Props) {
  const lines = pattern.split('').map((value, index) => ({
    lineNumber: index + 1,
    yang: value === '1',
  })).reverse()
  return (
    <ol className="hexagram-diagram" aria-label="Hexagram lines, top line first">
      {lines.map(({ lineNumber, yang }) => {
        const changing = changingLines.includes(lineNumber)
        return (
          <li key={lineNumber} className={changing ? 'is-changing' : undefined}>
            <span className="line-number">Line {lineNumber}</span>
            <span className={`hex-line ${yang ? 'hex-line--yang' : 'hex-line--yin'}`} aria-label={yang ? 'yang line' : 'yin line'}>
              {yang ? <span /> : <><span /><span /></>}
            </span>
            <span className="line-state">{changing ? `Changing${values[lineNumber] ? ` · ${values[lineNumber]}` : ''}` : yang ? 'Yang' : 'Yin'}</span>
          </li>
        )
      })}
    </ol>
  )
}
