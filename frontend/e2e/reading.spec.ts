import { expect, test, type Page } from '@playwright/test'

async function createReading(page: Page, title: string) {
  await page.goto('/readings/new')
  await page.getByLabel('Title').fill(title)
  await page.getByLabel('Question optional').fill('What is present?')
  await page.getByRole('button', { name: 'Create reading' }).click()
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
}

test('Tarot draw displays local knowledge and remains identical after reload', async ({ page }) => {
  await createReading(page, 'Tarot browser smoke')
  await page.getByRole('button', { name: 'Draw cards' }).click()
  const card = page.locator('.tarot-card').first()
  await expect(card).toBeVisible()
  const cardName = await card.getByRole('heading').textContent()
  const cardAlt = await card.getByRole('img').getAttribute('alt')
  const firstFact = card.locator('.fact').first()
  if (!(await firstFact.getAttribute('open'))) await firstFact.locator('summary').first().click()
  await expect(firstFact.locator('.source-text').first()).toBeVisible()
  await expect(firstFact.getByText('Provenance').first()).toBeVisible()
  await expect(card.getByRole('img')).toHaveAttribute('src', /\/api\/v1\/items\/.+\/image/)
  await page.reload()
  await expect(page.locator('.tarot-card').first().getByRole('heading')).toHaveText(cardName || '')
  await expect(page.locator('.tarot-card').first().getByRole('img')).toHaveAttribute('alt', cardAlt || '')
  await page.getByLabel('Add a note').fill('Persist this observation.')
  await page.getByRole('button', { name: 'Save note' }).click()
  await expect(page.getByText('Persist this observation.')).toBeVisible()
})

test('I Ching casts display six persisted lines and both backend methods', async ({ page }) => {
  await createReading(page, 'I Ching browser smoke')
  await page.getByRole('button', { name: 'I Ching', exact: true }).click()
  await page.getByRole('button', { name: 'Cast I Ching' }).click()
  const firstCast = page.locator('.cast-block').first()
  await expect(firstCast.getByText('Primary hexagram')).toBeVisible()
  await expect(firstCast.locator('.hexagram-panel').first().locator('.hexagram-diagram li')).toHaveCount(6)
  const identity = await firstCast.locator('.hexagram-title h4').first().textContent()
  await page.reload()
  await expect(page.locator('.cast-block').first().locator('.hexagram-title h4').first()).toHaveText(identity || '')
  await page.getByRole('button', { name: 'I Ching', exact: true }).click()
  await page.getByLabel(/Yarrow Stalk/).check()
  await page.getByRole('button', { name: 'Cast I Ching' }).click()
  await expect(page.getByRole('heading', { name: 'Yarrow stalk' })).toBeVisible()
  await expect(page.getByText('Casting details').last()).toBeVisible()
})

test('Elder Futhark draws three unique persisted runes with historical layers', async ({ page }) => {
  await createReading(page, 'Rune browser smoke')
  await page.getByRole('button', { name: 'Runes', exact: true }).click()
  await page.getByRole('button', { name: '3', exact: true }).click()
  await expect(page.getByText(/finite 24-rune set without replacement/)).toBeVisible()
  await expect(page.getByLabel(/reversed/i)).toHaveCount(0)
  await expect(page.getByLabel(/blank/i)).toHaveCount(0)
  await page.getByRole('button', { name: 'Draw runes' }).click()
  const cards = page.locator('.rune-card')
  await expect(cards).toHaveCount(3)
  const identities = await cards.locator('.rune-card__identity h4').allTextContents()
  expect(new Set(identities).size).toBe(3)
  await expect(cards.first().locator('.rune-glyph')).not.toHaveText('')
  await expect(cards.first().getByText('Historical evidence')).toBeVisible()
  await expect(cards.first().getByText('Reconstruction', { exact: true })).toBeVisible()
  await expect(cards.first().getByText(/Anglo-Saxon Futhorc|Younger Futhark/).first()).toBeVisible()
  await expect(cards.first().getByText('Modern English').first()).toBeVisible()
  await expect(cards.first().locator('.translation-text').first()).not.toHaveText('')
  await expect(cards.first().getByText(/modern, derived, machine-assisted/i).first()).toBeVisible()
  await expect(cards.first().getByText(/Historical original/i).first()).toBeVisible()
  const firstTranslation = await cards.first().locator('.translation-text').first().textContent()
  await page.reload()
  await expect(page.locator('.rune-card')).toHaveCount(3)
  expect(await page.locator('.rune-card__identity h4').allTextContents()).toEqual(identities)
  await expect(page.locator('.rune-card').first().locator('.translation-text').first()).toHaveText(firstTranslation || '')
})

test('reading history remains usable at a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await createReading(page, 'Mobile reading')
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
