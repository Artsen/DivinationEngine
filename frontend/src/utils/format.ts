const labels: Record<string, string> = {
  upright: 'Divinatory meaning',
  reversed: 'Reversed meaning',
  divinatory: 'Divinatory meaning',
  symbolism: 'Symbolism',
  description: 'Description',
  commentary: 'Commentary',
  hebrew_letter: 'Hebrew letter',
  golden_dawn_attribution: 'Golden Dawn attribution',
  'gua-ci': 'Judgment',
  'great-image': 'Great Image',
  tuan: 'Tuan',
  'yao-ci': 'Line text',
  'line-image': 'Line Xiang',
}

export function taxonomyLabel(value: string): string {
  return labels[value] ?? value.replaceAll('-', ' ').replaceAll('_', ' ').replace(/^./, (c) => c.toUpperCase())
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function castTypeLabel(value: string): string {
  return value === 'collection' ? 'Tarot' : value === 'iching' ? 'I Ching' : taxonomyLabel(value)
}
