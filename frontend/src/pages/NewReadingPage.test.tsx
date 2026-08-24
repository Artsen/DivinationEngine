import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { NewReadingPage } from './NewReadingPage'
import { jsonResponse, renderApp } from '../test/render'

afterEach(() => vi.unstubAllGlobals())

it('creates a reading and enters its workspace route', async () => {
  const fetchMock = vi.fn(() => jsonResponse({ id: 'new-id', title: 'A question', question: null, cast_count: 0, cast_types: [], created_at: '2026-08-23T18:00:00Z', updated_at: '2026-08-23T18:00:00Z' }))
  vi.stubGlobal('fetch', fetchMock)
  renderApp(<Routes><Route path="/readings/new" element={<NewReadingPage />} /><Route path="/readings/:id" element={<h1>Workspace opened</h1>} /></Routes>, ['/readings/new'])
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Title'), 'A question')
  await user.click(screen.getByRole('button', { name: 'Create reading' }))
  expect(await screen.findByRole('heading', { name: 'Workspace opened' })).toBeVisible()
  expect(fetchMock).toHaveBeenCalledWith('/api/v1/readings', expect.objectContaining({ method: 'POST' }))
})
