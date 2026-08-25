import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { spreadsApi } from '../api/spreads'
import type { Spread, SpreadCreate, SpreadPatch } from '../api/types'
import { ErrorState, LoadingState } from '../components/AsyncState'

interface DraftPosition { key?: string; label: string; description: string }

const blankPositions = (): DraftPosition[] => [
  { label: 'First position', description: '' },
  { label: 'Second position', description: '' },
  { label: 'Third position', description: '' },
]

export function SpreadsPage() {
  const queryClient = useQueryClient()
  const headingRef = useRef<HTMLHeadingElement>(null)
  const spreads = useQuery({ queryKey: ['spreads'], queryFn: spreadsApi.list })
  const [editing, setEditing] = useState<Spread | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [systemTypes, setSystemTypes] = useState<string[]>(['tarot'])
  const [positions, setPositions] = useState<DraftPosition[]>(blankPositions)

  useEffect(() => { document.title = 'Spreads · DivinationEngine' }, [])

  const clear = () => {
    setEditing(null)
    setName('')
    setDescription('')
    setSystemTypes(['tarot'])
    setPositions(blankPositions())
  }
  const save = useMutation({
    mutationFn: () => {
      const positionPayload = positions.map((position, index) => ({
        ...(position.key ? { key: position.key } : {}),
        label: position.label,
        description: position.description || null,
        rotation: 0,
        order: index + 1,
      }))
      if (editing) {
        const body: SpreadPatch = { name, description: description || null, positions: positionPayload }
        return spreadsApi.update(editing.id, body)
      }
      const body: SpreadCreate = { name, description: description || null, system_types: systemTypes, positions: positionPayload }
      return spreadsApi.create(body)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['spreads'] })
      clear()
      headingRef.current?.focus()
    },
  })
  const builtins = spreads.data?.filter((spread) => spread.origin === 'builtin') ?? []
  const custom = spreads.data?.filter((spread) => spread.origin === 'custom') ?? []

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }
  function toggleSystem(system: string) {
    setSystemTypes((current) => current.includes(system)
      ? current.length === 1 ? current : current.filter((value) => value !== system)
      : [...current, system])
  }
  function edit(spread: Spread) {
    setEditing(spread)
    setName(spread.name)
    setDescription(spread.description ?? '')
    setSystemTypes(spread.system_types)
    setPositions(spread.positions.map((position) => ({ key: position.key, label: position.label, description: position.description ?? '' })))
    document.querySelector('.spread-editor')?.scrollIntoView({ behavior: 'smooth' })
  }
  function updatePosition(index: number, field: 'label' | 'description', value: string) {
    setPositions((current) => current.map((position, positionIndex) => positionIndex === index ? { ...position, [field]: value } : position))
  }
  function move(index: number, direction: -1 | 1) {
    const target = index + direction
    if (target < 0 || target >= positions.length) return
    setPositions((current) => {
      const next = [...current]
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  }

  return <main className="page spreads-page">
    <header className="page-heading"><div><p className="eyebrow">Reading structure</p><h1 ref={headingRef} tabIndex={-1}>Spreads</h1><p>Arrange drawn cards or runes into named semantic positions. These layouts are modern editorial tools, not historical evidence.</p></div></header>
    {spreads.isPending && <LoadingState>Loading spreads…</LoadingState>}
    {spreads.isError && <ErrorState message="Unable to load spreads." />}
    {spreads.data && <div className="spread-workspace">
      <section className="spread-library" aria-labelledby="built-in-spreads">
        <h2 id="built-in-spreads">Built-in layouts</h2>
        <p className="muted">Project-provided modern layouts. They are available to every reading and cannot be edited.</p>
        <div className="spread-card-grid">{builtins.map((spread) => <SpreadCard key={spread.id} spread={spread} />)}</div>
        <div className="section-heading"><div><p className="eyebrow">Your workspace</p><h2>Your spreads</h2></div><span>{custom.length}</span></div>
        {custom.length === 0 ? <div className="guided-empty"><h3>No custom spreads yet.</h3><p>Create one with the editor. Its position labels and descriptions will be stored with each cast.</p></div> : <div className="spread-card-grid">{custom.map((spread) => <SpreadCard key={spread.id} spread={spread} onEdit={() => edit(spread)} />)}</div>}
      </section>
      <section className="spread-editor" aria-labelledby="spread-editor-heading">
        <p className="eyebrow">{editing ? 'Edit custom layout' : 'Custom layout'}</p>
        <h2 id="spread-editor-heading">{editing ? `Edit ${editing.name}` : 'Create a spread'}</h2>
        <form onSubmit={submit}>
          <label htmlFor="spread-name">Name</label><input id="spread-name" required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} />
          <label htmlFor="spread-description">Description <small>optional</small></label><textarea id="spread-description" rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
          <fieldset disabled={Boolean(editing)}><legend>Works with</legend><label className="check-row"><input type="checkbox" checked={systemTypes.includes('tarot')} onChange={() => toggleSystem('tarot')} /> Tarot</label><label className="check-row"><input type="checkbox" checked={systemTypes.includes('runes')} onChange={() => toggleSystem('runes')} /> Runes</label></fieldset>
          <fieldset className="position-editor"><legend>Positions</legend>
            {positions.map((position, index) => <div className="position-editor__row" key={position.key ?? index}>
              <span className="position-number">{index + 1}</span>
              <div><label htmlFor={`position-${index}`}>Position label</label><input id={`position-${index}`} required value={position.label} onChange={(event) => updatePosition(index, 'label', event.target.value)} /><label htmlFor={`description-${index}`}>Meaning <small>optional</small></label><input id={`description-${index}`} value={position.description} onChange={(event) => updatePosition(index, 'description', event.target.value)} /></div>
              <div className="position-actions"><button type="button" className="button-text" disabled={index === 0} onClick={() => move(index, -1)} aria-label={`Move ${position.label || `position ${index + 1}`} up`}>↑</button><button type="button" className="button-text" disabled={index === positions.length - 1} onClick={() => move(index, 1)} aria-label={`Move ${position.label || `position ${index + 1}`} down`}>↓</button>{!editing && <button type="button" className="button-text" disabled={positions.length === 1} onClick={() => setPositions((current) => current.filter((_, positionIndex) => positionIndex !== index))} aria-label={`Remove ${position.label || `position ${index + 1}`}`}>Remove</button>}</div>
            </div>)}
            {!editing && <button type="button" className="button-secondary" onClick={() => setPositions((current) => [...current, { label: `Position ${current.length + 1}`, description: '' }])}>Add position</button>}
            {editing && <p className="form-hint">Position labels, descriptions, and order can be edited. Position count and system applicability remain fixed after creation to protect references.</p>}
          </fieldset>
          <div className="form-actions"><button className="button-primary" type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : editing ? 'Save changes' : 'Create spread'}</button>{editing && <button className="button-secondary" type="button" onClick={clear}>Cancel</button>}</div>
          {save.error && <p className="form-error" role="alert">{save.error.message}</p>}
        </form>
      </section>
    </div>}
  </main>
}

function SpreadCard({ spread, onEdit }: { spread: Spread; onEdit?: () => void }) {
  return <article className="spread-card"><header><div><p className="eyebrow">{spread.origin === 'builtin' ? 'Built in' : 'Custom'} · {spread.positions.length} positions</p><h3>{spread.name}</h3></div>{onEdit && <button type="button" className="button-text" onClick={onEdit}>Edit</button>}</header>{spread.description && <p>{spread.description}</p>}<div className="system-tags">{spread.system_types.map((system) => <span key={system}>{system}</span>)}</div><ol>{spread.positions.map((position) => <li key={position.id}><strong>{position.label}</strong>{position.description && <span>{position.description}</span>}</li>)}</ol><small>{spread.origin === 'builtin' ? 'Modern editorial layout · not historical evidence.' : 'Custom user-authored layout.'}</small></article>
}
