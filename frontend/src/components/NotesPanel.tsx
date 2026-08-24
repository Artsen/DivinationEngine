import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { readingsApi } from '../api/readings'
import type { Note } from '../api/types'
import { formatDate } from '../utils/format'

export function NotesPanel({ readingId, notes }: { readingId: string; notes: Note[] }) {
  const queryClient = useQueryClient()
  const [body, setBody] = useState('')
  const [editing, setEditing] = useState<string | null>(null)
  const [editBody, setEditBody] = useState('')
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['reading', readingId] })
  const add = useMutation({ mutationFn: (value: string) => readingsApi.addNote(readingId, value), onSuccess: () => { setBody(''); refresh() } })
  const update = useMutation({ mutationFn: ({ id, value }: { id: string; value: string }) => readingsApi.updateNote(readingId, id, value), onSuccess: () => { setEditing(null); refresh() } })
  const remove = useMutation({ mutationFn: (id: string) => readingsApi.deleteNote(readingId, id), onSuccess: refresh })

  function submit(event: FormEvent) {
    event.preventDefault()
    if (body.trim()) add.mutate(body.trim())
  }

  return (
    <section className="notes-panel" aria-labelledby="notes-heading">
      <div className="section-heading"><div><p className="eyebrow">Reflection</p><h2 id="notes-heading">Notes</h2></div></div>
      {notes.length === 0 && <p className="muted">No notes yet.</p>}
      <div className="notes-list">
        {notes.map((note) => (
          <article key={note.id} className="note">
            {editing === note.id ? (
              <form onSubmit={(event) => { event.preventDefault(); if (editBody.trim()) update.mutate({ id: note.id, value: editBody.trim() }) }}>
                <label htmlFor={`note-${note.id}`}>Edit note</label>
                <textarea id={`note-${note.id}`} value={editBody} onChange={(event) => setEditBody(event.target.value)} required />
                <div className="button-row"><button type="submit" disabled={update.isPending}>Save</button><button type="button" className="button-secondary" onClick={() => setEditing(null)}>Cancel</button></div>
              </form>
            ) : (
              <>
                <p>{note.body}</p>
                <footer><time dateTime={note.updated_at}>{formatDate(note.updated_at)}</time><div><button type="button" className="button-text" onClick={() => { setEditing(note.id); setEditBody(note.body) }}>Edit</button><button type="button" className="button-text button-danger" onClick={() => remove.mutate(note.id)} disabled={remove.isPending}>Delete</button></div></footer>
              </>
            )}
          </article>
        ))}
      </div>
      <form onSubmit={submit} className="note-form">
        <label htmlFor="new-note">Add a note</label>
        <textarea id="new-note" value={body} onChange={(event) => setBody(event.target.value)} placeholder="Record what stands out…" required />
        <button type="submit" disabled={add.isPending || !body.trim()}>{add.isPending ? 'Saving…' : 'Save note'}</button>
        {(add.error || update.error || remove.error) && <p role="alert" className="form-error">Unable to save the note. Please try again.</p>}
      </form>
    </section>
  )
}
