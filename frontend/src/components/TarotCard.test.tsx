import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import type { ContextDrawResult, ContextSource, ContextTradition } from '../api/types'
import { TarotCard } from './TarotCard'

const source: ContextSource = { id: 'waite', key: 'waite', title: 'The Pictorial Key to the Tarot', author: 'A. E. Waite', edition: '1922', publisher: null, publication_year: 1922, language: 'en', citation: null, source_url: 'https://example.test/waite', rights_status: 'public_domain', notes: null }
const tradition: ContextTradition = { id: 'gd', slug: 'golden-dawn', name: 'Golden Dawn', description: null }
const result = {
  id: 'result', draw_order: 1, orientation: 'reversed', placement: null,
  item: { id: 'fool', collection_id: 'rws', slug: 'the-fool', name: 'The Fool', display_name: 'The Fool', sequence: 0, symbol: null, metadata: {} },
  knowledge: {
    applicable_interpretations: [{ id: 'meaning', key: 'meaning', item_id: 'fool', source_id: 'waite', tradition_id: null, interpretation_type: 'reversed', exact_text: 'Negligence and carelessness.', locator: 'The Fool', sequence: 1, notes: null }],
    other_interpretations: [],
    correspondences: [{ id: 'air', key: 'air', item_id: 'fool', source_id: 'waite', tradition_id: 'gd', type: 'golden_dawn_attribution', value: 'Air', status: 'tradition_specific', locator: 'Book T', notes: null }],
    rune_poems: [],
  },
} as ContextDrawResult

it('renders a reversed visual card with text, accessibility, and distinct provenance', async () => {
  render(<TarotCard result={result} sources={{ waite: source }} traditions={{ gd: tradition }} />)
  expect(screen.getByRole('img', { name: 'The Fool — reversed' })).toBeVisible()
  expect(screen.getByRole('img').parentElement).toHaveClass('tarot-card__image-frame--reversed')
  expect(screen.getByText('Negligence and carelessness.')).toBeVisible()
  expect(screen.getByText('Correspondences')).toBeVisible()
  await userEvent.click(screen.getByText('Correspondences'))
  expect(screen.getByText('Golden Dawn · Golden Dawn attribution')).toBeVisible()
  expect(screen.getAllByText('The Pictorial Key to the Tarot').length).toBeGreaterThan(0)
})
