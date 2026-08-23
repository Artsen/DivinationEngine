import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { readingsApi } from '../api/readings'
import type { Collection, ContextCast } from '../api/types'

interface Props {
  readingId: string
  collections: Collection[]
  casts: ContextCast[]
  ichingReady: boolean
}

export function CastControls({ readingId, collections, casts, ichingReady }: Props) {
  const queryClient = useQueryClient()
  const [kind, setKind] = useState<'tarot' | 'iching'>('tarot')
  const [count, setCount] = useState(1)
  const [reversals, setReversals] = useState(true)
  const [method, setMethod] = useState<'three-coin' | 'yarrow-stalk'>('three-coin')
  const [sessionId, setSessionId] = useState('')
  const rws = collections.find((row) => row.slug === 'rws-1909')
  const sessions = Array.from(new Map(casts.filter((cast) => cast.collection_id === rws?.id && cast.deck_session_id).map((cast) => [cast.deck_session_id!, cast])).values())
  const refresh = async () => {
    setSessionId('')
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['reading', readingId] }),
      queryClient.invalidateQueries({ queryKey: ['readings'] }),
    ])
  }
  const draw = useMutation({
    mutationFn: () => readingsApi.draw(readingId, {
      collection_id: rws!.id,
      count,
      reversals_enabled: reversals,
      ...(sessionId ? { deck_session_id: sessionId } : {}),
    }),
    onSuccess: refresh,
  })
  const cast = useMutation({ mutationFn: () => readingsApi.castIChing(readingId, { method }), onSuccess: refresh })
  const activeError = draw.error || cast.error

  function submit(event: FormEvent) {
    event.preventDefault()
    if (kind === 'tarot' && rws) draw.mutate()
    if (kind === 'iching' && ichingReady) cast.mutate()
  }

  return (
    <section className="cast-controls" aria-labelledby="new-cast-heading">
      <div><p className="eyebrow">Add to this reading</p><h2 id="new-cast-heading">New cast</h2></div>
      <div className="segmented" role="group" aria-label="Cast type">
        <button type="button" aria-pressed={kind === 'tarot'} onClick={() => setKind('tarot')}>Tarot / Card Draw</button>
        <button type="button" aria-pressed={kind === 'iching'} onClick={() => setKind('iching')}>I Ching</button>
      </div>
      <form onSubmit={submit}>
        {kind === 'tarot' ? (
          rws ? <>
            <label htmlFor="deck">Deck</label><select id="deck" value={rws.id} disabled><option value={rws.id}>{rws.name}</option></select>
            <fieldset><legend>Draw count</legend><div className="count-options">{[1, 3].map((value) => <button key={value} type="button" aria-pressed={count === value} onClick={() => setCount(value)}>{value}</button>)}<label htmlFor="custom-count">Custom</label><input id="custom-count" type="number" min="1" max={rws.item_count} value={count} onChange={(event) => setCount(Number(event.target.value))} /></div></fieldset>
            <label className="check-row"><input type="checkbox" checked={reversals} onChange={(event) => setReversals(event.target.checked)} /> Allow reversed cards</label>
            <label htmlFor="deck-session">Deck session</label>
            <select id="deck-session" value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
              <option value="">Fresh shuffled deck</option>
              {sessions.map((session) => <option key={session.deck_session_id} value={session.deck_session_id!}>Continue deck from cast {session.cast_order}</option>)}
            </select>
            <p className="form-hint">{sessionId ? 'Cards already drawn from this persisted deck cannot repeat.' : 'A fresh cast starts with the complete deck.'}</p>
          </> : <div className="setup-message"><strong>RWS corpus is not installed.</strong><p>Run <code>divination-dev-bootstrap</code> in the backend terminal, then reload.</p></div>
        ) : (
          ichingReady ? <fieldset><legend>Method</legend><label className="radio-row"><input type="radio" name="method" value="three-coin" checked={method === 'three-coin'} onChange={() => setMethod('three-coin')} /><span><strong>Three Coin</strong><small>Six backend-generated coin throws</small></span></label><label className="radio-row"><input type="radio" name="method" value="yarrow-stalk" checked={method === 'yarrow-stalk'} onChange={() => setMethod('yarrow-stalk')} /><span><strong>Yarrow Stalk</strong><small>Traditional-style 18-manipulation reconstruction</small></span></label></fieldset> : <div className="setup-message"><strong>I Ching corpus is not installed.</strong><p>Run <code>divination-dev-bootstrap</code> in the backend terminal, then reload.</p></div>
        )}
        <button className="button-primary" type="submit" disabled={draw.isPending || cast.isPending || (kind === 'tarot' ? !rws : !ichingReady)}>{draw.isPending || cast.isPending ? 'Casting…' : kind === 'tarot' ? 'Draw cards' : 'Cast I Ching'}</button>
        {activeError && <p className="form-error" role="alert">{activeError.message}</p>}
      </form>
    </section>
  )
}
