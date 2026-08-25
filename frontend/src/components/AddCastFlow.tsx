import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { readingsApi } from '../api/readings'
import type { Collection, ContextCast, Spread } from '../api/types'

interface Props {
  readingId: string
  collections: Collection[]
  casts: ContextCast[]
  spreads: Spread[]
  ichingReady: boolean
  runesReady: boolean
}

type CastKind = 'tarot' | 'iching' | 'runes'

const choices: { kind: CastKind; name: string; description: string }[] = [
  { kind: 'tarot', name: 'Tarot', description: 'Draw one or more cards from the Rider–Waite–Smith deck.' },
  { kind: 'iching', name: 'I Ching', description: 'Generate six lines with coins or the yarrow-stalk procedure.' },
  { kind: 'runes', name: 'Runes', description: 'Draw from the finite 24-rune Elder Futhark set.' },
]

export function AddCastFlow({ readingId, collections, casts, spreads, ichingReady, runesReady }: Props) {
  const queryClient = useQueryClient()
  const triggerRef = useRef<HTMLButtonElement>(null)
  const restoreFocus = useRef(false)
  const [open, setOpen] = useState(false)
  const [kind, setKind] = useState<CastKind | null>(null)
  const [count, setCount] = useState(1)
  const [reversals, setReversals] = useState(true)
  const [method, setMethod] = useState<'three-coin' | 'yarrow-stalk'>('three-coin')
  const [sessionId, setSessionId] = useState('')
  const [spreadId, setSpreadId] = useState('')
  const rws = collections.find((row) => row.slug === 'rws-1909')
  const runes = collections.find((row) => row.slug === 'elder-futhark')
  const selectedCollection = kind === 'runes' ? runes : rws
  const selectedSpread = spreads.find((spread) => spread.id === spreadId)
  const compatibleSpreads = kind === 'tarot' || kind === 'runes'
    ? spreads.filter((spread) => spread.system_types.includes(kind))
    : []
  const effectiveCount = selectedSpread ? selectedSpread.positions.length : count
  const sessions = Array.from(new Map(casts
    .filter((cast) => cast.collection_id === selectedCollection?.id && cast.deck_session_id)
    .map((cast) => [cast.deck_session_id!, cast])).values())

  useEffect(() => {
    if (!open && restoreFocus.current) {
      triggerRef.current?.focus()
      restoreFocus.current = false
    }
  }, [open])

  const reset = () => {
    restoreFocus.current = true
    setOpen(false)
    setKind(null)
    setCount(1)
    setReversals(true)
    setMethod('three-coin')
    setSessionId('')
    setSpreadId('')
  }
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['reading', readingId] }),
      queryClient.invalidateQueries({ queryKey: ['readings'] }),
    ])
    reset()
  }
  const draw = useMutation({
    mutationFn: () => readingsApi.draw(readingId, {
      collection_id: selectedCollection!.id,
      count: effectiveCount,
      reversals_enabled: kind === 'tarot' && reversals,
      ...(spreadId ? { spread_id: spreadId } : {}),
      ...(sessionId ? { deck_session_id: sessionId } : {}),
    }),
    onSuccess: refresh,
  })
  const cast = useMutation({ mutationFn: () => readingsApi.castIChing(readingId, { method }), onSuccess: refresh })
  const pending = draw.isPending || cast.isPending
  const activeError = draw.error || cast.error
  const available = (choice: CastKind) => choice === 'tarot'
    ? Boolean(rws)
    : choice === 'iching'
      ? ichingReady
      : runesReady && Boolean(runes)

  function choose(next: CastKind) {
    if (available(next)) {
      setKind(next)
      setCount(1)
      setSessionId('')
      setSpreadId('')
    }
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    if ((kind === 'tarot' && rws) || (kind === 'runes' && runes)) draw.mutate()
    if (kind === 'iching') cast.mutate()
  }

  const layoutSelector = (kind === 'tarot' || kind === 'runes') && <fieldset className="layout-selector">
    <legend>Choose a layout</legend>
    <label htmlFor="spread-layout">Spread</label>
    <select id="spread-layout" value={spreadId} onChange={(event) => setSpreadId(event.target.value)}>
      <option value="">Unstructured draw</option>
      <optgroup label="Built in">
        {compatibleSpreads.filter((spread) => spread.origin === 'builtin').map((spread) => <option key={spread.id} value={spread.id}>{spread.name} ({spread.positions.length})</option>)}
      </optgroup>
      <optgroup label="Your spreads">
        {compatibleSpreads.filter((spread) => spread.origin === 'custom').map((spread) => <option key={spread.id} value={spread.id}>{spread.name} ({spread.positions.length})</option>)}
      </optgroup>
    </select>
    {selectedSpread ? <div className="layout-summary">
      <strong>{selectedSpread.name} · {selectedSpread.positions.length} positions</strong>
      {selectedSpread.description && <p>{selectedSpread.description}</p>}
      <ol>{selectedSpread.positions.map((position) => <li key={position.id}><strong>{position.label}</strong>{position.description && <span>{position.description}</span>}</li>)}</ol>
      <small>{selectedSpread.origin === 'builtin' ? 'Modern editorial layout · not historical evidence.' : 'Custom user-authored layout · not historical evidence.'}</small>
    </div> : <p className="form-hint">Cards or runes will be drawn without semantic positions.</p>}
    <Link className="button-text" to="/spreads">Manage custom spreads</Link>
  </fieldset>

  return <section className="add-cast" aria-labelledby="add-cast-heading">
    {!open ? <button ref={triggerRef} className="add-cast__trigger" type="button" onClick={() => setOpen(true)} aria-expanded="false"><span aria-hidden="true">+</span><span><strong id="add-cast-heading">Add a cast</strong><small>Tarot, I Ching, or Runes</small></span></button> : <div className="add-cast__panel">
      <header className="flow-heading"><div><p className="eyebrow">Add to this reading</p><h2 id="add-cast-heading">Choose a system</h2></div><button className="button-text" type="button" onClick={reset}>Close</button></header>
      <div className="system-choices" role="group" aria-label="Divination system">{choices.map((choice) => { const ready = available(choice.kind); return <button key={choice.kind} type="button" className="system-choice" aria-label={choice.name} aria-describedby={`${choice.kind}-description`} aria-pressed={kind === choice.kind} disabled={!ready} onClick={() => choose(choice.kind)}><strong>{choice.name}</strong><span id={`${choice.kind}-description`}>{choice.description}</span>{!ready && <small>Not installed</small>}</button> })}</div>
      {!kind && <p className="flow-prompt">Select an available system to see only the choices needed for this cast.</p>}
      {kind && <form className="cast-form" onSubmit={submit}>
        {kind === 'tarot' && rws && <><div className="selection-summary"><span>Deck</span><strong>{rws.name}</strong></div>{layoutSelector}{!selectedSpread && <fieldset><legend>How many cards?</legend><div className="count-options">{[1, 3].map((value) => <button key={value} type="button" aria-pressed={count === value} onClick={() => setCount(value)}>{value}</button>)}<label htmlFor="custom-count">Custom</label><input id="custom-count" type="number" min="1" max={rws.item_count} value={count} onChange={(event) => setCount(Number(event.target.value))} /></div></fieldset>}<label className="check-row"><input type="checkbox" checked={reversals} onChange={(event) => setReversals(event.target.checked)} /> Allow reversed cards</label></>}
        {kind === 'iching' && <fieldset><legend>Choose a casting method</legend><p className="form-hint">Both methods create six stored lines, beginning with the bottom line.</p><label className="radio-row"><input type="radio" name="method" value="three-coin" checked={method === 'three-coin'} onChange={() => setMethod('three-coin')} /><span><strong>Three coin</strong><small>Six coin throws generated by the backend</small></span></label><label className="radio-row"><input type="radio" name="method" value="yarrow-stalk" checked={method === 'yarrow-stalk'} onChange={() => setMethod('yarrow-stalk')} /><span><strong>Yarrow stalk</strong><small>An 18-manipulation software reconstruction</small></span></label></fieldset>}
        {kind === 'runes' && runes && <><div className="selection-summary"><span>Rune set</span><strong>{runes.name}</strong></div>{layoutSelector}{!selectedSpread && <fieldset><legend>How many runes?</legend><div className="count-options">{[1, 3].map((value) => <button key={value} type="button" aria-pressed={count === value} onClick={() => setCount(value)}>{value}</button>)}<label htmlFor="rune-custom-count">Custom</label><input id="rune-custom-count" type="number" min="1" max="24" value={count} onChange={(event) => setCount(Number(event.target.value))} /></div></fieldset>}<p className="form-hint">Draws use the finite set without replacement. No blank rune or reversals.</p></>}
        {(kind === 'tarot' || kind === 'runes') && sessions.length > 0 && <details className="advanced-options"><summary>Advanced options</summary><label htmlFor="deck-session">Continue a previous {kind === 'runes' ? 'rune bag' : 'deck'}</label><select id="deck-session" value={sessionId} onChange={(event) => setSessionId(event.target.value)}><option value="">Start fresh</option>{sessions.map((session) => <option key={session.deck_session_id} value={session.deck_session_id!}>Continue from cast {session.cast_order}</option>)}</select><p className="form-hint">Continuing prevents items already drawn in that session from appearing again.</p></details>}
        <button className="button-primary" type="submit" disabled={pending}>{pending ? 'Adding cast…' : kind === 'tarot' ? 'Draw cards' : kind === 'iching' ? 'Cast I Ching' : 'Draw runes'}</button>{activeError && <p className="form-error" role="alert">{activeError.message}</p>}
      </form>}
      {!rws || !ichingReady || !runesReady || !runes ? <p className="setup-note">Unavailable systems can be installed with <code>divination-dev-bootstrap</code>.</p> : null}
    </div>}
  </section>
}
