import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import type { Spread } from '../api/types'
import { jsonResponse, renderApp } from '../test/render'
import { SpreadsPage } from './SpreadsPage'

const builtin = {
  id: 'single', slug: 'single-card', name: 'Single Card', description: 'One point of focus.', origin: 'builtin',
  classification: 'modern-editorial-layout', system_types: ['tarot'], source_label: 'DivinationEngine project-provided layout',
  positions: [{ id: 'focus', key: 'focus', label: 'Focus', description: 'The central matter.', x: 0.5, y: 0.5, rotation: 0, order: 1 }],
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
} as Spread

afterEach(() => vi.unstubAllGlobals())

it('separates immutable built-ins and creates an ordered custom spread', async () => {
  const fetchMock = vi.fn<typeof fetch>().mockImplementation((_input, init) => init?.method === 'POST' ? jsonResponse({ ...builtin, id: 'custom', origin: 'custom', name: 'My Layout' }) : jsonResponse([builtin]))
  vi.stubGlobal('fetch', fetchMock)
  renderApp(<SpreadsPage />, ['/spreads'])
  expect(await screen.findByRole('heading', { name: 'Single Card' })).toBeVisible()
  expect(screen.getByText(/cannot be edited/)).toBeVisible()
  expect(screen.getByText(/No custom spreads yet/)).toBeVisible()

  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Name'), 'My Layout')
  const positionLabels = screen.getAllByLabelText('Position label')
  await user.clear(positionLabels[0])
  await user.type(positionLabels[0], 'Question')
  await user.click(screen.getByRole('button', { name: 'Add position' }))
  await user.click(screen.getByRole('button', { name: 'Create spread' }))

  const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
  expect(post).toBeDefined()
  const body = JSON.parse(String(post?.[1]?.body))
  expect(body.system_types).toEqual(['tarot'])
  expect(body.positions).toHaveLength(4)
  expect(body.positions[0]).toMatchObject({ label: 'Question', order: 1 })
  expect(within(screen.getByRole('main')).getByText(/modern editorial tools/i)).toBeVisible()
})
