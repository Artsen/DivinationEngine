import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import type { ContextDrawResult, ContextSource, ContextTradition } from '../api/types'
import { RuneCard } from './RuneCard'

const source: ContextSource = { id: 'poem-source', key: 'wikisource-rune-poems', title: 'Rune poems', author: null, edition: null, publisher: 'Wikisource contributors', publication_year: null, language: 'Old English and Old Norse', citation: null, source_url: 'https://en.wikisource.org/wiki/Rune_poems', rights_status: 'historical_source_text_public_domain', notes: null }
const reconstructionSource: ContextSource = { ...source, id: 'ut', key: 'ut', title: 'Old Norse Online, Lesson 10' }
const traditions: Record<string, ContextTradition> = {
  futhorc: { id: 'futhorc', slug: 'anglo-saxon-futhorc', name: 'Anglo-Saxon Futhorc', description: null },
  younger: { id: 'younger', slug: 'younger-futhark', name: 'Younger Futhark', description: null },
  reconstruction: { id: 'reconstruction', slug: 'proto-germanic-reconstruction', name: 'Proto-Germanic reconstruction', description: null },
}
const result = {
  id: 'draw', draw_order: 1, orientation: 'none', placement: null,
  item: { id: 'fehu', collection_id: 'elder', slug: 'fehu', name: 'Fehu', display_name: 'ᚠ Fehu', sequence: 1, symbol: 'ᚠ', metadata: { row_position: 1, aett: 1, position_in_aett: 1, transliteration: 'f', sound_value: '/f/', proto_germanic_name: 'fehu', reconstruction_status: 'reconstructed', lexical_reconstruction: 'cattle, possessions' } },
  knowledge: {
    applicable_interpretations: [],
    other_interpretations: [
      { id: 'oe', key: 'oe', item_id: 'fehu', source_id: 'poem-source', tradition_id: 'futhorc', interpretation_type: 'rune-poem', exact_text: 'Feoh byþ frofur fira gehwylcum;', locator: 'The Anglo-Saxon Rune Poem, stanza 1: Feoh', sequence: 1, notes: 'direct mapping. Exact redistributable English translation is not bundled.' },
      { id: 'no', key: 'no', item_id: 'fehu', source_id: 'poem-source', tradition_id: 'younger', interpretation_type: 'rune-poem', exact_text: 'Fé vældr frænda róge;', locator: 'The Norwegian Rune Poem, stanza 1: Fé', sequence: 1, notes: 'direct mapping. Exact redistributable English translation is not bundled.' },
    ],
    correspondences: [{ id: 'name', key: 'name', item_id: 'fehu', source_id: 'ut', tradition_id: 'reconstruction', type: 'reconstructed_name', value: 'fehu', status: 'reconstructed', locator: 'Older Futhark chart', notes: null }],
  },
} as ContextDrawResult

it('renders identity, reconstruction, layered source poems, rights notice, and provenance', async () => {
  render(<RuneCard result={result} sources={{ 'poem-source': source, ut: reconstructionSource }} traditions={traditions} />)
  expect(screen.getByRole('heading', { name: 'Fehu' })).toBeVisible()
  expect(screen.getByText('ᚠ')).toBeVisible()
  expect(screen.getByText(/Elder Futhark #1/)).toBeVisible()
  expect(screen.getByText('cattle, possessions')).toBeVisible()
  expect(screen.getByText('Feoh byþ frofur fira gehwylcum;')).toBeVisible()
  expect(screen.getByText('Rune poems · Anglo-Saxon Futhorc')).toBeVisible()
  expect(screen.getByText('Rune poems · Younger Futhark')).toBeVisible()
  expect(screen.getAllByText('Exact redistributable English translation is not bundled.')).toHaveLength(2)
  await userEvent.click(screen.getByText('Reconstruction'))
  expect(screen.getAllByText('Reconstructed').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Provenance').length).toBeGreaterThan(0)
  expect(screen.queryByText(/reversed meaning/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/blank rune/i)).not.toBeInTheDocument()
})
