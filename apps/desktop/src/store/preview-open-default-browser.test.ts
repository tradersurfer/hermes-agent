import { beforeEach, describe, expect, it } from 'vitest'

import { $dismissedPanes, $layoutTree } from '@/components/pane-shell/tree/store'

import { $previewTabs, closeRightRail, DEFAULT_BROWSER_URL, normalizeBrowserUrl, openDefaultBrowser } from './preview'

beforeEach(() => {
  closeRightRail()
  $dismissedPanes.set(new Set())
  $layoutTree.set(null)
})

describe('openDefaultBrowser', () => {
  it('loads the default page into a new browser when none is open', () => {
    openDefaultBrowser()

    const tabs = $previewTabs.get()

    expect(tabs).toHaveLength(1)
    expect(tabs[0]?.target.url).toBe(DEFAULT_BROWSER_URL)
  })

  it('does not replace a browser that already has a page', () => {
    openDefaultBrowser()
    const [first] = $previewTabs.get()

    // A second press re-fronts the same tab instead of navigating it away.
    openDefaultBrowser()

    const tabs = $previewTabs.get()

    expect(tabs).toHaveLength(1)
    expect(tabs[0]?.id).toBe(first?.id)
    expect(tabs[0]?.target.url).toBe(DEFAULT_BROWSER_URL)
  })

  it('navigates to an explicit URL, adding https to a bare host', () => {
    openDefaultBrowser()
    openDefaultBrowser('example.com/path')

    const tabs = $previewTabs.get()

    expect(tabs).toHaveLength(1)
    expect(tabs[0]?.target.url).toBe('https://example.com/path')
  })
})

describe('normalizeBrowserUrl', () => {
  it('keeps an explicit scheme and trims whitespace', () => {
    expect(normalizeBrowserUrl('  http://localhost:3000 ')).toBe('http://localhost:3000')
    expect(normalizeBrowserUrl('gemini.google.com/business')).toBe('https://gemini.google.com/business')
  })
})
