import { describe, expect, it } from 'vitest'
import { calculateImageSize, DEFAULT_SIZE_RULE, normalizeCodexCliImageSize, normalizeImageSize, prependCodexCliSizePrompt, stripInjectedCodexCliSizePrompt, validateImageSize } from './size'
import { getProfileForModel } from './modelProfile'

describe('calculateImageSize', () => {
  it('uses common 16:9 display resolutions for the built-in tiers', () => {
    expect(calculateImageSize('1K', '16:9')).toBe('1152x640')
    expect(calculateImageSize('2K', '16:9')).toBe('2048x1152')
  })

  it('uses matching portrait presets for common ratios', () => {
    expect(calculateImageSize('2K', '9:16')).toBe('1152x2048')
    expect(calculateImageSize('2K', '2:3')).toBe('1280x1920')
    expect(calculateImageSize('2K', '3:4')).toBe('1536x2048')
  })

  it('falls back to budget-based sizing for custom ratios', () => {
    expect(calculateImageSize('2K', '5:4')).toBe('1984x1600')
  })
})

describe('Codex CLI size compatibility', () => {
  it('normalizes custom sizes to the 1K pixel budget', () => {
    expect(normalizeCodexCliImageSize('2048x2048')).toBe('1024x1024')
    expect(normalizeCodexCliImageSize('2048x1536')).toBe('1024x768')
    expect(normalizeCodexCliImageSize('1536x1024')).toBe('1536x1024')
  })

  it('preserves non-preset ratios approximately and clamps excessive ratios', () => {
    expect(normalizeCodexCliImageSize('2500x2000')).toBe('1152x896')
    const [width, height] = normalizeCodexCliImageSize('4000x1000').split('x').map(Number)
    expect(width / height).toBeCloseTo(3, 2)
    expect(width * height).toBeLessThanOrEqual(1_572_864)
  })

  it('prepends a concise resolution hint only for explicit sizes', () => {
    expect(prependCodexCliSizePrompt('Draw a cat.\n', '1024x1024')).toBe('Generate at 1024x1024 resolution. Draw a cat.\n')
    expect(prependCodexCliSizePrompt('Generate at 1024x1024 resolution. Draw a cat.', '1024x1024')).toBe('Generate at 1024x1024 resolution. Draw a cat.')
    expect(prependCodexCliSizePrompt('Draw a cat.', 'auto')).toBe('Draw a cat.')
  })

  it('strips only the matching injected resolution hint', () => {
    expect(stripInjectedCodexCliSizePrompt('Generate at 1024x1024 resolution. Draw a cat.', 'Draw a cat.', '1024x1024')).toBe('Draw a cat.')
    expect(stripInjectedCodexCliSizePrompt('Generate at 2048x2048 resolution. Draw a cat.', 'Draw a cat.', '1024x1024')).toBe('Generate at 2048x2048 resolution. Draw a cat.')
    expect(stripInjectedCodexCliSizePrompt('Generate at 1024x1024 resolution. Draw a cat.', 'Generate at 1024x1024 resolution. Draw a cat.', '1024x1024')).toBe('Generate at 1024x1024 resolution. Draw a cat.')
    expect(stripInjectedCodexCliSizePrompt('Generate at 1024x1024 resolution. Draw a cat.', 'Draw a cat.', 'auto')).toBe('Generate at 1024x1024 resolution. Draw a cat.')
  })
})

describe('profile size rules', () => {
  const qwenRule = getProfileForModel('Qwen-Image-2.1').sizeRule

  it('keeps every official Qwen preset unchanged', () => {
    const presets = getProfileForModel('Qwen-Image-2.1').officialResolutions
    expect(presets).toHaveLength(8)
    for (const preset of presets) {
      expect(normalizeImageSize(`${preset.width}x${preset.height}`, qwenRule))
        .toBe(`${preset.width}x${preset.height}`)
    }
  })

  it('still applies the generic clamp when no rule is given', () => {
    const normalized = normalizeImageSize('2752x1536')
    const [width, height] = normalized.split('x').map(Number)
    expect(Math.max(width, height)).toBeLessThanOrEqual(2048)
    expect(width % 64).toBe(0)
    expect(height % 64).toBe(0)
    expect(normalizeImageSize('1024x1024')).toBe('1024x1024')
    expect(normalizeImageSize('auto')).toBe('auto')
  })

  it('passes valid custom sizes through under the Qwen rule', () => {
    expect(validateImageSize(1024, 1024, qwenRule)).toEqual([])
    expect(validateImageSize(2752, 1536, qwenRule)).toEqual([])
    expect(validateImageSize(2400, 1792, qwenRule)).toEqual([])
    expect(validateImageSize(1536, 2752, qwenRule)).toEqual([])
    expect(validateImageSize(512, 512, qwenRule)).toEqual([])
  })

  it('reports the specific rule violated by a custom size', () => {
    const multipleError = validateImageSize(1032, 1024, qwenRule)
    expect(multipleError).toHaveLength(1)
    expect(multipleError[0]).toContain('16 的倍数')

    const pixelsError = validateImageSize(2400, 1808, qwenRule)
    expect(pixelsError).toHaveLength(1)
    expect(pixelsError[0]).toContain('4300800')

    const aspectError = validateImageSize(2752, 1472, qwenRule)
    expect(aspectError).toHaveLength(1)
    expect(aspectError[0]).toContain('1.8:1')

    const edgeError = validateImageSize(2768, 1552, qwenRule)
    expect(edgeError).toHaveLength(1)
    expect(edgeError[0]).toContain('512-2752px')

    expect(validateImageSize(3000, 2768, qwenRule).length).toBeGreaterThan(1)
    expect(validateImageSize(0, 1024, qwenRule)).toEqual(['宽和高必须是正整数'])
  })

  it('keeps the generic default rule values', () => {
    expect(DEFAULT_SIZE_RULE).toEqual({
      minEdge: 512,
      maxEdge: 2048,
      minPixels: 262_144,
      maxPixels: 4_194_304,
      maxAspectRatio: 3,
      multiple: 64,
    })
    expect(validateImageSize(1000, 1000, DEFAULT_SIZE_RULE)).toHaveLength(1)
    expect(validateImageSize(1000, 1000, DEFAULT_SIZE_RULE)[0]).toContain('64 的倍数')
  })
})
