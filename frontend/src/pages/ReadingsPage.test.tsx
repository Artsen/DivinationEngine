import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ReadingsPage } from './ReadingsPage'
import { jsonResponse, renderApp } from '../test/render'

afterEach(() => vi.unstubAllGlobals())

describe('readings list', () => {
  it('shows persisted readings and cast summaries', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse([{ id: 'reading-1', title: 'Crossroads', question: 'What now?', cast_count: 2, cast_types: ['collection', 'iching'], created_at: '2026-08-23T18:00:00Z', updated_at: '2026-08-23T18:00:00Z' }])))
    renderApp(<ReadingsPage />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading readings')
    expect(await screen.findByRole('heading', { name: 'Crossroads' })).toBeVisible()
    expect(screen.getByText('2 casts')).toBeVisible()
    expect(screen.getByText('Tarot · I Ching')).toBeVisible()
  })

  it('shows a readable server error', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({ detail: 'broken' }, 500)))
    renderApp(<ReadingsPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load readings')
  })
})
