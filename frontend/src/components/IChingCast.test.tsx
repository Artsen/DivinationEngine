import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import type { ContextCast, Hexagram } from '../api/types'
import { HexagramDiagram } from './HexagramDiagram'
import { IChingCast } from './IChingCast'

const text = (key: string, unit_type: string, language: string, exact_text: string, line_position: number | null = null) => ({ key, layer: 'zhouyi-core', unit_type, line_position, section: null, language, source_id: 'legge', tradition_id: 'received', exact_text, locator: 'SBE XVI', sequence: 1, notes: null })
const primary: Hexagram = { key: 'hexagram-01', canonical_number: 1, binary_pattern: '111111', chinese_name: '乾', pinyin: 'Qián', legge_title: 'The Khien Hexagram', glyph: '䷀', texts: [text('gua-zh', 'gua-ci', 'zh-Hant', '元亨利貞。'), text('gua-en', 'gua-ci', 'en', 'Khien represents what is great.'), text('line-en', 'yao-ci', 'en', 'The dragon appears.', 3)] }
const relating: Hexagram = { ...primary, key: 'hexagram-02', canonical_number: 2, binary_pattern: '000000', chinese_name: '坤', pinyin: 'Kūn', legge_title: 'The Khwăn Hexagram', glyph: '䷁', texts: [text('kun-en', 'gua-ci', 'en', 'Khwăn represents what is receptive.')] }
const baseCast = {
  id: 'cast', cast_type: 'iching', collection_id: null, deck_session_id: null, cast_order: 1, configuration: {}, created_at: '2026-08-23T18:00:00Z', draw_results: [], spread: null,
  iching: { method: 'three-coin', pattern_order: 'bottom_to_top', primary_pattern: '111111', changing_lines: [3], relating_pattern: '000000', throws: [1,2,3,4,5,6].map((line_number) => ({ line_number, coins: [3,3,3], line_value: line_number === 3 ? 9 : 7, procedure: null })), knowledge: { primary, relating, changing_lines: [3], selection_notice: 'No interpretive-school rule is applied.' } },
} as ContextCast

it('displays bottom-to-top API lines in conventional top-to-bottom visual order', () => {
  render(<HexagramDiagram pattern="101010" changingLines={[6]} values={{ 6: 9 }} />)
  const lines = screen.getByRole('list').querySelectorAll('li')
  expect(within(lines[0] as HTMLElement).getByText('Line 6')).toBeVisible()
  expect(within(lines[5] as HTMLElement).getByText('Line 1')).toBeVisible()
  expect(within(lines[0] as HTMLElement).getByText('Changing · 9')).toBeVisible()
})

it('renders primary, relating, changing lines, original Chinese, and source details', async () => {
  render(<IChingCast cast={baseCast} sources={{ legge: { id: 'legge', key: 'legge', title: 'The Yî King', author: 'James Legge', edition: null, publisher: null, publication_year: 1882, language: 'en', citation: null, source_url: null, rights_status: 'public_domain', notes: null } }} traditions={{ received: { id: 'received', slug: 'received-yijing', name: 'Received Yijing', description: null } }} />)
  expect(screen.getByText('Primary hexagram')).toBeVisible()
  expect(screen.getByText('Relating hexagram')).toBeVisible()
  expect(screen.getByText('元亨利貞。')).not.toBeVisible()
  await userEvent.click(screen.getAllByText('Traditional Chinese text')[0])
  expect(screen.getByText('元亨利貞。')).toBeVisible()
  expect(screen.getAllByText('Changing · 9').length).toBeGreaterThan(0)
  expect(screen.getAllByText('The Yî King').length).toBeGreaterThan(0)
  expect(screen.getByText('How this cast was generated')).toBeVisible()
})

it('does not fabricate a relating panel when no lines change', () => {
  const noChange = structuredClone(baseCast)
  noChange.iching!.changing_lines = []
  noChange.iching!.knowledge!.changing_lines = []
  render(<IChingCast cast={noChange} sources={{}} traditions={{}} />)
  expect(screen.queryByText('Relating hexagram')).not.toBeInTheDocument()
  expect(screen.getByText('There are no changing lines in this cast.')).toBeVisible()
})
