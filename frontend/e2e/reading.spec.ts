import { expect, test, type Page } from '@playwright/test'

async function createReading(page: Page, title: string) {
  await page.goto('/readings/new')
  await page.getByLabel('Title').fill(title)
  await page.getByLabel('Question optional').fill('What is present?')
  await page.getByRole('button', { name: 'Create reading' }).click()
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
}

async function chooseSystem(page: Page, name: 'Tarot' | 'I Ching' | 'Runes') {
  await page.getByRole('button', { name: /Add a cast/ }).click()
  await page.getByRole('button', { name, exact: true }).click()
}

async function expectNoHorizontalOverflow(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 })
  const dimensions = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
  }))
  expect(dimensions).toEqual({ documentWidth: width, viewportWidth: width })
}

test('Tarot built-in spread persists semantic positions and local knowledge', async ({ page }) => {
  await createReading(page, 'Tarot browser smoke')
  await chooseSystem(page, 'Tarot')
  await page.getByLabel('Spread').selectOption({ label: 'Situation / Challenge / Advice (3)' })
  await page.getByRole('button', { name: 'Draw cards' }).click()
  await expect(page.locator('.placement-heading')).toHaveCount(3)
  await expect(page.locator('.placement-heading').nth(0)).toContainText('Situation')
  await expect(page.locator('.placement-heading').nth(1)).toContainText('Challenge')
  await expect(page.locator('.placement-heading').nth(2)).toContainText('Advice')
  const card = page.locator('.tarot-card').first()
  await expect(card).toBeVisible()
  const cardName = await card.locator(':scope > header:not(.placement-heading) h4').textContent()
  const cardAlt = await card.getByRole('img').getAttribute('alt')
  await expect(card.locator('.primary-meaning .source-text').first()).toBeVisible()
  await card.getByText('Source', { exact: true }).first().click()
  await card.getByText('Provenance').first().click()
  await expect(card.getByText('The Pictorial Key to the Tarot').first()).toBeVisible()
  await expect(card.getByRole('img')).toHaveAttribute('src', /\/api\/v1\/items\/.+\/image/)
  await page.reload()
  await expect(page.locator('.tarot-card').first().locator(':scope > header:not(.placement-heading) h4')).toHaveText(cardName || '')
  await expect(page.locator('.tarot-card').first().getByRole('img')).toHaveAttribute('alt', cardAlt || '')
  await expect(page.locator('.placement-heading')).toHaveCount(3)
  await page.getByLabel('Add a note').fill('Persist this observation.')
  await page.getByRole('button', { name: 'Save note' }).click()
  await expect(page.getByText('Persist this observation.')).toBeVisible()
})

test('I Ching casts display six persisted lines and both backend methods', async ({ page }) => {
  await createReading(page, 'I Ching browser smoke')
  await chooseSystem(page, 'I Ching')
  await page.getByRole('button', { name: 'Cast I Ching' }).click()
  const firstCast = page.locator('.cast-block').first()
  await expect(firstCast.getByText('Primary hexagram')).toBeVisible()
  await expect(firstCast.locator('.hexagram-panel').first().locator('.hexagram-diagram li')).toHaveCount(6)
  const identity = await firstCast.locator('.hexagram-title h4').first().textContent()
  await page.reload()
  await expect(page.locator('.cast-block').first().locator('.hexagram-title h4').first()).toHaveText(identity || '')
  await chooseSystem(page, 'I Ching')
  await page.getByLabel(/Yarrow stalk/).check()
  await page.getByRole('button', { name: 'Cast I Ching' }).click()
  await expect(page.getByText(/Yarrow stalk · 6 lines/).last()).toBeVisible()
  await expect(page.getByText('How this cast was generated').last()).toBeVisible()
  await expect(page.locator('.cast-block--latest')).toContainText('Cast 2 · Latest')
})

test('Elder Futhark spread persists positions without historical-layout claims', async ({ page }) => {
  await createReading(page, 'Rune browser smoke')
  await chooseSystem(page, 'Runes')
  await page.getByLabel('Spread').selectOption({ label: 'Past / Present / Future (3)' })
  await expect(page.getByText(/finite set without replacement/)).toBeVisible()
  await expect(page.getByLabel(/reversed/i)).toHaveCount(0)
  await expect(page.getByLabel(/blank/i)).toHaveCount(0)
  await page.getByRole('button', { name: 'Draw runes' }).click()
  const cards = page.locator('.rune-card')
  await expect(cards).toHaveCount(3)
  await expect(page.locator('.placement-heading')).toHaveCount(3)
  await expect(page.getByText(/not evidence of an ancient Germanic casting method/i)).toBeVisible()
  const identities = await cards.locator('.rune-card__identity h4').allTextContents()
  expect(new Set(identities).size).toBe(3)
  await expect(cards.first().locator('.rune-glyph')).not.toHaveText('')
  await expect(cards.first().getByText('Historical evidence')).toBeVisible()
  await expect(cards.first().getByText('Reconstruction', { exact: true })).toBeVisible()
  const connections = cards.first().locator('.tradition-connections')
  await connections.locator(':scope > summary').click()
  await expect(connections.getByText('Elder Futhark', { exact: true })).toHaveCount(1)
  await expect(connections.getByText('Anglo-Saxon Futhorc', { exact: true })).toHaveCount(1)
  expect(await connections.locator('.tradition-chip').count()).toBeGreaterThan(1)
  const poemWitnesses = cards.first().locator('.poem-witness')
  await cards.first().locator('.knowledge-stack > details > summary').filter({ hasText: 'Rune poems' }).click()
  const poemCount = await poemWitnesses.count()
  expect(poemCount).toBeGreaterThan(0)
  if (poemCount > 1) {
    for (let index = 0; index < poemCount; index += 1) await expect(poemWitnesses.nth(index)).not.toHaveAttribute('open', '')
    await poemWitnesses.first().locator(':scope > summary').click()
  } else {
    await expect(poemWitnesses.first()).toHaveAttribute('open', '')
  }
  await expect(poemWitnesses.first().getByText('Modern English')).toBeVisible()
  await expect(poemWitnesses.first().locator('.translation-text')).not.toHaveText('')
  await expect(poemWitnesses.first().getByText(/modern, derived, machine-assisted/i)).toBeVisible()
  await expect(poemWitnesses.first().getByText(/Historical original/i)).toBeVisible()
  if (poemCount > 1) await expect(poemWitnesses.nth(1)).not.toHaveAttribute('open', '')
  const firstTranslation = await poemWitnesses.first().locator('.translation-text').textContent()
  await page.reload()
  await expect(page.locator('.rune-card')).toHaveCount(3)
  await expect(page.locator('.placement-heading')).toHaveCount(3)
  expect(await page.locator('.rune-card__identity h4').allTextContents()).toEqual(identities)
  const persistedWitness = page.locator('.rune-card').first().locator('.poem-witness').first()
  await page.locator('.rune-card').first().locator('.knowledge-stack > details > summary').filter({ hasText: 'Rune poems' }).click()
  await expect(page.locator('.rune-card').first().locator('.poem-witness')).toHaveCount(poemCount)
  if (poemCount > 1) await persistedWitness.locator(':scope > summary').click()
  await expect(persistedWitness.locator('.translation-text')).toHaveText(firstTranslation || '')
  await page.setViewportSize({ width: 390, height: 844 })
  const runeCardWidth = await page.locator('.rune-card').first().evaluate((element) => ({
    client: element.clientWidth,
    scroll: element.scrollWidth,
  }))
  expect(runeCardWidth.scroll).toBeLessThanOrEqual(runeCardWidth.client)
  await expect(page.locator('.rune-card').first().locator('.tradition-chip')).toHaveCount(3)
})

test('custom spread can be created and applied to a five-card cast', async ({ page }) => {
  await page.goto('/spreads')
  await page.getByLabel('Name').fill('Career Decision')
  const labels = ['Current situation', 'Opportunity', 'Risk']
  const inputs = page.getByLabel('Position label')
  for (let index = 0; index < labels.length; index += 1) await inputs.nth(index).fill(labels[index])
  await page.getByRole('button', { name: 'Add position' }).click()
  await page.getByRole('button', { name: 'Add position' }).click()
  await inputs.nth(3).fill('Advice')
  await inputs.nth(4).fill('Likely direction')
  await page.getByLabel('Meaning optional').first().fill('The present conditions, constraints, resources, and relationships that frame this decision right now.')
  await page.getByRole('button', { name: 'Create spread' }).click()
  await expect(page.getByRole('heading', { name: 'Career Decision' })).toBeVisible()

  await createReading(page, 'Custom spread browser smoke')
  await chooseSystem(page, 'Tarot')
  await page.getByLabel('Spread').selectOption({ label: 'Career Decision (5)' })
  await page.getByRole('button', { name: 'Draw cards' }).click()
  await expect(page.locator('.tarot-card')).toHaveCount(5)
  await expect(page.locator('.placement-heading')).toHaveCount(5)
  await expect(page.locator('.placement-heading').last()).toContainText('Likely direction')
  for (const width of [1440, 768, 390]) await expectNoHorizontalOverflow(page, width)
  await expect(page.locator('.spread-result-layout')).toHaveCSS('display', 'grid')
})

test('unstructured draw retains the legacy grid without fake semantic positions', async ({ page }) => {
  await createReading(page, 'Unstructured browser smoke')
  await chooseSystem(page, 'Tarot')
  await expect(page.getByLabel('Spread')).toHaveValue('')
  await page.getByRole('button', { name: '3', exact: true }).click()
  await page.getByRole('button', { name: 'Draw cards' }).click()
  await expect(page.locator('.tarot-card')).toHaveCount(3)
  await expect(page.locator('.placement-heading')).toHaveCount(0)
  await expect(page.getByText(/Unstructured draw/).first()).toBeVisible()
})

test('reading history remains usable at a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await createReading(page, 'Mobile reading')
  await expect(page.getByText('This reading is ready for its first cast.')).toBeVisible()
  await page.getByRole('link', { name: 'All readings' }).click()
  await expect(page.getByRole('link', { name: 'New reading' }).first()).toBeVisible()
  await expect(page.locator('.reading-card').first()).toBeVisible()
  const overflow = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
    elements: Array.from(document.querySelectorAll('body *'))
      .filter((element) => element.getBoundingClientRect().right > document.documentElement.clientWidth + 1)
      .slice(0, 8)
      .map((element) => ({
        tag: element.tagName,
        className: element.className,
        right: element.getBoundingClientRect().right,
        text: element.textContent?.slice(0, 80),
      })),
  }))
  expect(overflow, JSON.stringify(overflow)).toEqual({ documentWidth: 390, viewportWidth: 390, elements: [] })
})
