import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { readingsApi } from '../api/readings'

export function NewReadingPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [question, setQuestion] = useState('')
  const create = useMutation({
    mutationFn: readingsApi.create,
    onSuccess: async (reading) => {
      await queryClient.invalidateQueries({ queryKey: ['readings'] })
      navigate(`/readings/${reading.id}`)
    },
  })
  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate({ title: title.trim(), question: question.trim() || null })
  }
  return (
    <main className="page page--narrow">
      <Link className="back-link" to="/readings">← Readings</Link>
      <section className="form-card">
        <p className="eyebrow">Begin</p><h1>New reading</h1><p>Name the moment. The question can remain open.</p>
        <form onSubmit={submit}>
          <label htmlFor="title">Title</label><input id="title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required placeholder="Sunday evening reflection" />
          <label htmlFor="question">Question <span>optional</span></label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What deserves my attention?" />
          <button type="submit" className="button-primary" disabled={create.isPending || !title.trim()}>{create.isPending ? 'Creating…' : 'Create reading'}</button>
          {create.isError && <p className="form-error" role="alert">Unable to create the reading. {create.error.message}</p>}
        </form>
      </section>
    </main>
  )
}
