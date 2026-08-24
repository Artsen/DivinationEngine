import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import type { Collection } from '../api/types'
import { renderApp } from '../test/render'
import { CastControls } from './CastControls'

const base = { description: null, metadata: {}, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }
const collections = [
  { ...base, id: 'rws', slug: 'rws-1909', name: 'RWS', system_type: 'tarot', supports_reversals: true, item_count: 78 },
  { ...base, id: 'runes', slug: 'elder-futhark', name: 'Elder Futhark', system_type: 'runes', supports_reversals: false, item_count: 24 },
] as Collection[]

it('offers runes only when ready and exposes no blank or reversal controls', async () => {
  renderApp(<CastControls readingId="reading" collections={collections} casts={[]} ichingReady runesReady />)
  await userEvent.click(screen.getByRole('button', { name: 'Runes' }))
  expect(screen.getByRole('button', { name: 'Draw runes' })).toBeVisible()
  expect(screen.getByRole('option', { name: 'Fresh rune bag' })).toBeVisible()
  expect(screen.getByText(/finite 24-rune set without replacement/)).toBeVisible()
  expect(screen.queryByLabelText(/reversed/i)).not.toBeInTheDocument()
  expect(screen.queryByLabelText(/blank/i)).not.toBeInTheDocument()
})

it('reports an independently missing rune corpus', async () => {
  renderApp(<CastControls readingId="reading" collections={collections.slice(0, 1)} casts={[]} ichingReady runesReady={false} />)
  await userEvent.click(screen.getByRole('button', { name: 'Runes' }))
  expect(screen.getByText('Elder Futhark corpus is not installed.')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Draw runes' })).toBeDisabled()
})
