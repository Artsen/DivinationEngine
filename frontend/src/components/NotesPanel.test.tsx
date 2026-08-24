import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { NotesPanel } from './NotesPanel'
import { jsonResponse, renderApp } from '../test/render'

afterEach(() => vi.unstubAllGlobals())

it('supports explicit add, edit, and delete note interactions', async () => {
  const fetchMock = vi.fn<typeof fetch>()
  fetchMock.mockImplementation(() => jsonResponse({ id: 'note', reading_id: 'reading', body: 'Saved', created_at: '2026-08-23T18:00:00Z', updated_at: '2026-08-23T18:00:00Z' }))
  vi.stubGlobal('fetch', fetchMock)
  renderApp(<NotesPanel readingId="reading" notes={[{ id: 'note', reading_id: 'reading', body: 'Original', created_at: '2026-08-23T18:00:00Z', updated_at: '2026-08-23T18:00:00Z' }]} />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Edit' }))
  await user.clear(screen.getByLabelText('Edit note'))
  await user.type(screen.getByLabelText('Edit note'), 'Changed')
  await user.click(screen.getByRole('button', { name: 'Save' }))
  await user.type(screen.getByLabelText('Add a note'), 'New note')
  await user.click(screen.getByRole('button', { name: 'Save note' }))
  await user.click(screen.getByRole('button', { name: 'Delete' }))
  expect(fetchMock).toHaveBeenCalledTimes(3)
  expect(fetchMock.mock.calls.map((call) => (call[1] as RequestInit).method)).toEqual(['PATCH', 'POST', 'DELETE'])
})
