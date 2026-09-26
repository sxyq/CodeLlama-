import { describe, expect, it } from 'vitest'
import { IMAGE_REQUEST_TIMEOUT_MS, imageRequestTimeoutMs } from './imageApiShared'

describe('image request timeout alignment', () => {
  it('uses the single constant of 1200s', () => {
    expect(IMAGE_REQUEST_TIMEOUT_MS).toBe(1_200_000)
    expect(IMAGE_REQUEST_TIMEOUT_MS).toBe(1200 * 1000)
    // frontend >= GPU wait (900s) and == queue timeout (1200s)
    expect(IMAGE_REQUEST_TIMEOUT_MS).toBeGreaterThanOrEqual(900 * 1000)
    expect(IMAGE_REQUEST_TIMEOUT_MS).toBe(1200 * 1000)
  })

  it('a profile timeout of 1199s does not cut requests early', () => {
    // effective abort delay must stay >= 1199s (no early termination)
    expect(imageRequestTimeoutMs(1199)).toBeGreaterThanOrEqual(1199 * 1000)
    expect(imageRequestTimeoutMs(1199)).toBe(1_200_000)
  })

  it('1200s is both the floor and the frontend cap', () => {
    expect(imageRequestTimeoutMs(1200)).toBe(1_200_000)
    expect(imageRequestTimeoutMs(600)).toBe(1_200_000) // old value cannot shorten
    expect(imageRequestTimeoutMs(1800)).toBe(1_200_000) // never above the cap
  })

  it('generation and edit resolve through the same helper', () => {
    expect(imageRequestTimeoutMs()).toBe(IMAGE_REQUEST_TIMEOUT_MS)
    expect(imageRequestTimeoutMs(undefined)).toBe(IMAGE_REQUEST_TIMEOUT_MS)
  })
})
