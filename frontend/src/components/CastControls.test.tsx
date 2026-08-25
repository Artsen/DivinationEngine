import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import type { Collection, Spread } from '../api/types'
import { jsonResponse, renderApp } from '../test/render'
import { AddCastFlow } from './AddCastFlow'

const base = { description: null, metadata: {}, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }
const collections = [
  { ...base, id: 'rws', slug: 'rws-1909', name: 'RWS', system_type: 'tarot', supports_reversals: true, item_count: 78 },
  { ...base, id: 'runes', slug: 'elder-futhark', name: 'Elder Futhark', system_type: 'runes', supports_reversals: false, item_count: 24 },
] as Collection[]
const spread = {
  id: 'spread-three', slug: 'past-present-future', name: 'Past / Present / Future', description: 'A three-position timeline.',
  origin: 'builtin', classification: 'modern-editorial-layout', system_types: ['tarot', 'runes'], source_label: 'DivinationEngine project-provided layout',
  positions: ['Past', 'Present', 'Future'].map((label, index) => ({ id: `position-${index}`, key: label.toLowerCase(), label, description: `${label} context`, x: index / 2, y: 0.5, rotation: 0, order: index + 1 })),
  created_at: base.created_at, updated_at: base.updated_at,
} as Spread

afterEach(() => vi.unstubAllGlobals())

it('offers runes only when ready and exposes no blank or reversal controls', async () => {
  renderApp(<AddCastFlow readingId="reading" collections={collections} casts={[]} spreads={[spread]} ichingReady runesReady />)
  await userEvent.click(screen.getByRole('button', { name: /Add a cast/ }))
  await userEvent.click(screen.getByRole('button', { name: 'Runes' }))
  expect(screen.getByRole('button', { name: 'Draw runes' })).toBeVisible()
  expect(screen.getByText(/finite set without replacement/)).toBeVisible()
  expect(screen.queryByText('Advanced options')).not.toBeInTheDocument()
  expect(screen.queryByLabelText(/reversed/i)).not.toBeInTheDocument()
  expect(screen.queryByLabelText(/blank/i)).not.toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Past / Present / Future (3)' })).toBeVisible()
})

it('reports an independently missing rune corpus', async () => {
  renderApp(<AddCastFlow readingId="reading" collections={collections.slice(0, 1)} casts={[]} spreads={[]} ichingReady runesReady={false} />)
  await userEvent.click(screen.getByRole('button', { name: /Add a cast/ }))
  expect(screen.getByRole('button', { name: 'Runes' })).toBeDisabled()
  expect(screen.getAllByText('Not installed')).toHaveLength(1)
  expect(screen.getByText(/Unavailable systems can be installed/)).toBeVisible()
})

it('reveals system-specific choices only after explicit selection and keeps sessions advanced', async () => {
  const cast = { id: 'cast', cast_type: 'collection', collection_id: 'rws', deck_session_id: 'opaque-id', cast_order: 2, configuration: {}, created_at: '2026-01-01T00:00:00Z', draw_results: [], iching: null } as never
  renderApp(<AddCastFlow readingId="reading" collections={collections} casts={[cast]} spreads={[]} ichingReady runesReady />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: /Add a cast/ }))
  expect(screen.queryByLabelText('How many cards?')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Tarot' }))
  expect(screen.getByText('Advanced options')).toBeVisible()
  expect(screen.getByLabelText(/Continue a previous deck/)).not.toBeVisible()
  await user.click(screen.getByText('Advanced options'))
  expect(screen.getByLabelText(/Continue a previous deck/)).toBeVisible()
  expect(screen.queryByText('opaque-id')).not.toBeInTheDocument()
})

it('supports keyboard entry and resets the flow after an explicit successful submit', async () => {
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(() => jsonResponse({ id: 'cast' }))
  vi.stubGlobal('fetch', fetchMock)
  renderApp(<AddCastFlow readingId="reading" collections={collections} casts={[]} spreads={[]} ichingReady runesReady />)
  const user = userEvent.setup()
  await user.tab()
  expect(screen.getByRole('button', { name: /Add a cast/ })).toHaveFocus()
  await user.keyboard('{Enter}')
  await user.click(screen.getByRole('button', { name: 'Tarot' }))
  await user.click(screen.getByRole('button', { name: 'Draw cards' }))
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).not.toHaveProperty('spread_id')
  expect(await screen.findByRole('button', { name: /Add a cast/ })).toHaveFocus()
})

it('derives draw count and placement request from the selected spread', async () => {
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(() => jsonResponse({ id: 'cast' }))
  vi.stubGlobal('fetch', fetchMock)
  renderApp(<AddCastFlow readingId="reading" collections={collections} casts={[]} spreads={[spread]} ichingReady runesReady />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: /Add a cast/ }))
  await user.click(screen.getByRole('button', { name: 'Tarot' }))
  await user.selectOptions(screen.getByLabelText('Spread'), spread.id)
  expect(screen.getByText('Past context')).toBeVisible()
  expect(screen.queryByText('How many cards?')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Draw cards' }))
  const [, options] = fetchMock.mock.calls[0]
  expect(JSON.parse(String(options?.body))).toMatchObject({ count: 3, spread_id: spread.id })
})
