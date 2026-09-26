import { describe, expect, it } from 'vitest'
import { createDefaultOpenAIProfile } from './apiProfiles'
import {
  applyServerCapability,
  DEFAULT_MODEL_PROFILE,
  getProfileForApiProfile,
  getProfileForModel,
  referenceLimitMessage,
} from './modelProfile'

describe('getProfileForModel', () => {
  it('returns the generic default profile for unknown or empty model ids', () => {
    expect(getProfileForModel('gpt-image-2.5-sunburst')).toBe(DEFAULT_MODEL_PROFILE)
    expect(getProfileForModel('')).toBe(DEFAULT_MODEL_PROFILE)
    expect(DEFAULT_MODEL_PROFILE.maxReferenceImages).toBe(16)
    expect(DEFAULT_MODEL_PROFILE.sizeRule.maxEdge).toBe(2048)
    expect(DEFAULT_MODEL_PROFILE.sizeRule.multiple).toBe(64)
    expect(DEFAULT_MODEL_PROFILE.officialResolutions).toEqual([])
    expect(DEFAULT_MODEL_PROFILE.strictSizeValidation).toBe(false)
    expect(DEFAULT_MODEL_PROFILE.referenceRoleLabels).toBe(false)
    expect(DEFAULT_MODEL_PROFILE.supportsRGBA).toBe(true)
  })

  it('matches Qwen-Image-2.1 across common id spellings', () => {
    for (const id of ['Qwen-Image-2.1', 'qwen-image-2-1', ' QWEN_IMAGE_2_1 ', 'qwenimage21']) {
      const profile = getProfileForModel(id)
      expect(profile.model).toBe('Qwen-Image-2.1')
      expect(profile.maxReferenceImages).toBe(5)
    }
  })

  it('mirrors capability.py values for Qwen-Image-2.1', () => {
    const profile = getProfileForModel('Qwen-Image-2.1')
    expect(profile.sizeRule.minEdge).toBe(512)
    expect(profile.sizeRule.maxEdge).toBe(2752)
    expect(profile.sizeRule.maxPixels).toBe(4_300_800)
    expect(profile.sizeRule.maxAspectRatio).toBe(1.8)
    expect(profile.sizeRule.multiple).toBe(16)
    expect(profile.qualitySteps).toEqual({ fast: 4, standard: 24, high: 40 })
    expect(profile.supportsMask).toBe(false)
    expect(profile.supportsStrength).toBe(false)
    expect(profile.supportsRGBA).toBe(false)
    expect(profile.strictSizeValidation).toBe(true)
    expect(profile.referenceRoleLabels).toBe(true)
    expect(profile.annotateQualitySteps).toBe(true)

    const expected = [
      [1024, 1024],
      [2048, 2048],
      [2400, 1792],
      [1792, 2400],
      [2528, 1696],
      [1696, 2528],
      [2752, 1536],
      [1536, 2752],
    ]
    expect(profile.officialResolutions).toHaveLength(8)
    profile.officialResolutions.forEach((preset, index) => {
      expect(preset.width).toBe(expected[index][0])
      expect(preset.height).toBe(expected[index][1])
      expect(preset.label).toBe(`${expected[index][0]}x${expected[index][1]}`)
    })
  })

  it('resolves the profile from an API config', () => {
    const qwen = createDefaultOpenAIProfile({ apiKey: 'test-key', model: 'Qwen-Image-2.1' })
    expect(getProfileForApiProfile(qwen).maxReferenceImages).toBe(5)
    const generic = createDefaultOpenAIProfile({ apiKey: 'test-key' })
    expect(getProfileForApiProfile(generic)).toBe(DEFAULT_MODEL_PROFILE)
  })
})

describe('referenceLimitMessage', () => {
  it('keeps the exact Qwen limit wording', () => {
    expect(referenceLimitMessage(getProfileForModel('Qwen-Image-2.1')))
      .toBe('Qwen-Image-2.1 当前服务器配置最多支持5张参考图。')
  })

  it('keeps the generic template wording', () => {
    expect(referenceLimitMessage(DEFAULT_MODEL_PROFILE))
      .toBe('参考图数量已达上限（16 张），无法继续添加')
  })
})

describe('applyServerCapability', () => {
  it('ignores null, garbage and unknown models without throwing', () => {
    expect(() => applyServerCapability(null)).not.toThrow()
    expect(() => applyServerCapability('nope')).not.toThrow()
    expect(() => applyServerCapability({})).not.toThrow()
    expect(() => applyServerCapability({ model: 'unknown-model', max_reference_images: 9 })).not.toThrow()
    expect(getProfileForModel('unknown-model')).toBe(DEFAULT_MODEL_PROFILE)
  })

  it('overrides static values from /status capability and keeps the rest', () => {
    applyServerCapability({
      model: 'Qwen-Image-2.1',
      max_reference_images: 3,
      min_edge: 512,
      max_edge: 2752,
      max_pixels: 4_300_800,
      max_aspect_ratio: 1.8,
      multiple_of: 16,
      quality_steps: { fast: 4, standard: 24, high: 40 },
      resolutions: [
        { label: '1024x1024', width: 1024, height: 1024, production: true },
        { label: 'hidden', width: 64, height: 64, production: false },
        { width: 'bad', height: 1 },
      ],
      supports_mask: false,
      supports_strength: false,
      supports_rgba: false,
    })

    const profile = getProfileForModel('Qwen-Image-2.1')
    expect(profile.maxReferenceImages).toBe(3)
    expect(profile.sizeRule.maxEdge).toBe(2752)
    expect(profile.qualitySteps.high).toBe(40)
    expect(profile.officialResolutions).toEqual([{ label: '1024x1024', width: 1024, height: 1024 }])
    expect(profile.referenceLimitMessage).toBe('Qwen-Image-2.1 当前服务器配置最多支持3张参考图。')
    expect(profile.supportsMask).toBe(false)
    expect(profile.strictSizeValidation).toBe(true)

    // 还原静态镜像，避免影响同文件后续用例
    applyServerCapability({
      model: 'Qwen-Image-2.1',
      max_reference_images: 5,
      min_edge: 512,
      max_edge: 2752,
      max_pixels: 4_300_800,
      max_aspect_ratio: 1.8,
      multiple_of: 16,
      quality_steps: { fast: 4, standard: 24, high: 40 },
      resolutions: [
        { label: '1024x1024', width: 1024, height: 1024 },
        { label: '2048x2048', width: 2048, height: 2048 },
        { label: '2400x1792', width: 2400, height: 1792 },
        { label: '1792x2400', width: 1792, height: 2400 },
        { label: '2528x1696', width: 2528, height: 1696 },
        { label: '1696x2528', width: 1696, height: 2528 },
        { label: '2752x1536', width: 2752, height: 1536 },
        { label: '1536x2752', width: 1536, height: 2752 },
      ],
      supports_mask: false,
      supports_strength: false,
      supports_rgba: false,
    })
    expect(getProfileForModel('Qwen-Image-2.1').maxReferenceImages).toBe(5)
    expect(getProfileForModel('Qwen-Image-2.1').officialResolutions).toHaveLength(8)
  })

  it('keeps static values for fields missing from the payload', () => {
    applyServerCapability({ model: 'Qwen-Image-2.1' })
    const profile = getProfileForModel('Qwen-Image-2.1')
    expect(profile.maxReferenceImages).toBe(5)
    expect(profile.sizeRule.multiple).toBe(16)
    expect(profile.officialResolutions).toHaveLength(8)
    expect(profile.supportsRGBA).toBe(false)
  })
})
