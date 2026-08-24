import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import type { ContextDrawResult, ContextSource, ContextTradition } from '../api/types'
import { RuneCard } from './RuneCard'

const source: ContextSource = { id: 'poem-source', key: 'wikisource-rune-poems', title: 'Rune poems', author: null, edition: null, publisher: 'Wikisource contributors', publication_year: null, language: 'Old English and Old Norse', citation: null, source_url: 'https://en.wikisource.org/wiki/Rune_poems', rights_status: 'historical_source_text_public_domain', notes: null }
const reconstructionSource: ContextSource = { ...source, id: 'ut', key: 'ut', title: 'Old Norse Online, Lesson 10' }
const dictionarySource: ContextSource = { ...source, id: 'bosworth', key: 'bosworth-toller-1898', title: 'An Anglo-Saxon Dictionary' }
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
    other_interpretations: [],
    correspondences: [{ id: 'name', key: 'name', item_id: 'fehu', source_id: 'ut', tradition_id: 'reconstruction', type: 'reconstructed_name', value: 'fehu', status: 'reconstructed', locator: 'Older Futhark chart', notes: null }],
    rune_poems: [{ id: 'oe', key: 'oe', item_id: 'fehu', source_id: 'poem-source', tradition_id: 'futhorc', poem: 'old-english', sequence: 1, rune_character: 'ᚠ', normalized_name: 'Feoh', language: 'ang', original_text: 'Feoh byþ frofur fira gehwylcum;', latin_tag: null, locator: 'The Anglo-Saxon Rune Poem, stanza 1: Feoh', mapping_status: 'direct', mapping_justification: 'Direct historical mapping.', editorial_translation: 'Wealth is a comfort to every person;', editorial_latin_gloss: null, translation_language: 'en', translation_type: 'project-editorial', translation_status: 'derived', translator: 'DivinationEngine editorial translation', machine_assisted: true, translation_source_ids: ['poem-source', 'bosworth'], translation_notes: 'Frofor can denote comfort or consolation.' }],
  },
} as ContextDrawResult

it('renders identity, reconstruction, distinct editorial and historical poem layers, and provenance', async () => {
  render(<RuneCard result={result} sources={{ 'poem-source': source, bosworth: dictionarySource, ut: reconstructionSource }} traditions={traditions} />)
  expect(screen.getByRole('heading', { name: 'Fehu' })).toBeVisible()
  expect(screen.getByText('ᚠ')).toBeVisible()
  expect(screen.getByText(/Elder Futhark #1/)).toBeVisible()
  expect(screen.getByText('cattle, possessions')).toBeVisible()
  expect(screen.getByText('Feoh byþ frofur fira gehwylcum;')).toBeVisible()
  expect(screen.getByText('Wealth is a comfort to every person;')).toBeVisible()
  expect(screen.getByText('Old English · Anglo-Saxon Futhorc')).toBeVisible()
  expect(screen.getByText(/modern, derived, machine-assisted/i)).toBeVisible()
  expect(screen.getByText(/not historical source text or divinatory meaning/i)).toBeVisible()
  expect(screen.getByText(/frofor can denote comfort/i)).toBeVisible()
  await userEvent.click(screen.getByText('Reconstruction'))
  expect(screen.getAllByText('Reconstructed').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Provenance').length).toBeGreaterThan(0)
  expect(screen.queryByText(/reversed meaning/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/blank rune/i)).not.toBeInTheDocument()
})
