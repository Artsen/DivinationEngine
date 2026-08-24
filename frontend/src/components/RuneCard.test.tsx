import { render, screen, within } from '@testing-library/react'
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
const oldEnglishPoem = { id: 'oe', key: 'oe', item_id: 'fehu', source_id: 'poem-source', tradition_id: 'futhorc', poem: 'old-english', sequence: 1, rune_character: 'ᚠ', normalized_name: 'Feoh', language: 'ang', original_text: 'Feoh byþ frofur fira gehwylcum;', latin_tag: null, locator: 'The Anglo-Saxon Rune Poem, stanza 1: Feoh', mapping_status: 'direct', mapping_justification: 'Direct historical mapping.', editorial_translation: 'Wealth is a comfort to every person;', editorial_latin_gloss: null, translation_language: 'en', translation_type: 'project-editorial', translation_status: 'derived', translator: 'DivinationEngine editorial translation', machine_assisted: true, translation_source_ids: ['poem-source', 'bosworth'], translation_notes: 'Frofor can denote comfort or consolation.' }
const norwegianPoem = { ...oldEnglishPoem, id: 'no', key: 'no', tradition_id: 'younger', poem: 'norwegian', normalized_name: 'Fé', language: 'non', original_text: 'Fé vældr frænda róge;', editorial_translation: 'Wealth causes strife among kinsmen;', translation_notes: null }
const icelandicPoem = { ...oldEnglishPoem, id: 'is', key: 'is', tradition_id: 'younger', poem: 'icelandic', normalized_name: 'Fé', language: 'non', original_text: 'Fé er frænda róg', editorial_translation: 'Wealth is strife among kinsmen,', translation_notes: null }
const result = {
  id: 'draw', draw_order: 1, orientation: 'none', placement: null,
  item: { id: 'fehu', collection_id: 'elder', slug: 'fehu', name: 'Fehu', display_name: 'ᚠ Fehu', sequence: 1, symbol: 'ᚠ', metadata: { row_position: 1, aett: 1, position_in_aett: 1, transliteration: 'f', sound_value: '/f/', proto_germanic_name: 'fehu', reconstruction_status: 'reconstructed', lexical_reconstruction: 'cattle, possessions', system: 'elder-futhark' } },
  knowledge: {
    applicable_interpretations: [],
    other_interpretations: [],
    correspondences: [{ id: 'name', key: 'name', item_id: 'fehu', source_id: 'ut', tradition_id: 'reconstruction', type: 'reconstructed_name', value: 'fehu', status: 'reconstructed', locator: 'Older Futhark chart', notes: null }],
    rune_poems: [oldEnglishPoem, norwegianPoem, icelandicPoem],
  },
} as ContextDrawResult

it('renders deduplicated system markers and independently collapsed poem witnesses', async () => {
  const user = userEvent.setup()
  render(<RuneCard result={result} sources={{ 'poem-source': source, bosworth: dictionarySource, ut: reconstructionSource }} traditions={traditions} />)
  expect(screen.getByRole('heading', { name: 'Fehu' })).toBeVisible()
  expect(screen.getByText('ᚠ')).toBeVisible()
  expect(screen.getByText(/Elder Futhark #1/)).toBeVisible()
  expect(screen.getByText('cattle, possessions')).toBeVisible()
  await user.click(screen.getByText('Related historical systems'))
  const connections = screen.getByRole('region', { name: 'Tradition connections' })
  expect(within(connections).getAllByText('Elder Futhark')).toHaveLength(1)
  expect(within(connections).getAllByText('Anglo-Saxon Futhorc')).toHaveLength(1)
  expect(within(connections).getAllByText('Younger Futhark')).toHaveLength(1)
  expect(within(connections).getByText('Core system')).toBeVisible()
  expect(within(connections).getAllByText('Related historical system')).toHaveLength(2)

  const witnessLabels = ['Old English Rune Poem', 'Norwegian Rune Poem', 'Icelandic Rune Poem']
  await user.click(screen.getAllByText('Rune poems').find((element) => element.tagName === 'SUMMARY')!)
  const witnesses = witnessLabels.map((label) => screen.getByText(label).closest('details'))
  expect(witnesses).toHaveLength(3)
  witnesses.forEach((witness) => expect(witness).not.toHaveAttribute('open'))

  await user.click(screen.getByText('Old English Rune Poem'))
  expect(witnesses[0]).toHaveAttribute('open')
  expect(witnesses[1]).not.toHaveAttribute('open')
  expect(witnesses[2]).not.toHaveAttribute('open')
  expect(within(witnesses[0]!).getByText('Feoh byþ frofur fira gehwylcum;')).toBeVisible()
  expect(within(witnesses[0]!).getByText('Wealth is a comfort to every person;')).toBeVisible()
  expect(within(witnesses[0]!).getByText(/modern, derived, machine-assisted/i)).toBeVisible()
  expect(within(witnesses[0]!).getByText(/not historical source text or divinatory meaning/i)).toBeVisible()
  expect(within(witnesses[0]!).getByText(/frofor can denote comfort/i)).toBeVisible()
  await user.click(screen.getByText('Reconstruction'))
  expect(screen.getAllByText('Reconstructed').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Provenance').length).toBeGreaterThan(0)
  expect(screen.queryByText(/reversed meaning/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/blank rune/i)).not.toBeInTheDocument()
})

it('exposes cautious related-system and poem mappings as readable text', () => {
  const cautiousResult = {
    ...result,
    item: { ...result.item, slug: 'algiz', name: 'Algiz' },
    knowledge: {
      ...result.knowledge,
      rune_poems: result.knowledge.rune_poems.map((poem) => ({
        ...poem,
        mapping_status: 'likely-related',
        mapping_justification: 'The later rune form is related but not identical evidence.',
      })),
    },
  } as ContextDrawResult
  render(<RuneCard result={cautiousResult} sources={{ 'poem-source': source, bosworth: dictionarySource, ut: reconstructionSource }} traditions={traditions} />)
  screen.getByText('Related historical systems').click()
  const connections = screen.getByRole('region', { name: 'Tradition connections' })
  expect(within(connections).getAllByText('Related system · cautious relationship')).toHaveLength(2)
  screen.getAllByText('Rune poems').find((element) => element.tagName === 'SUMMARY')!.click()
  expect(screen.getAllByText(/Related with caution/)).toHaveLength(3)
})
