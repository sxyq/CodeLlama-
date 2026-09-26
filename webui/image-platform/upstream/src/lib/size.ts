const SIZE_PATTERN = /^\s*(\d+)\s*[xX×]\s*(\d+)\s*$/
const RATIO_PATTERN = /^\s*(\d+(?:\.\d+)?)\s*[:xX×]\s*(\d+(?:\.\d+)?)\s*$/
const SIZE_MULTIPLE = 64
const MAX_EDGE = 2048
const MIN_EDGE = 512
const MAX_ASPECT_RATIO = 3
const MIN_PIXELS = 262_144
const MAX_PIXELS = 4_194_304
const MAX_1K_PIXELS = 1_572_864

/** 尺寸规则：按模型 Profile 取值（见 lib/modelProfile.ts） */
export interface SizeRule {
  minEdge: number
  maxEdge: number
  minPixels: number
  maxPixels: number
  maxAspectRatio: number
  multiple: number
}

/** 通用默认规则 = 现有 gpt-image 行为（512-2048、64 倍数、宽高比 ≤3、262144-4194304 像素） */
export const DEFAULT_SIZE_RULE: SizeRule = {
  minEdge: MIN_EDGE,
  maxEdge: MAX_EDGE,
  minPixels: MIN_PIXELS,
  maxPixels: MAX_PIXELS,
  maxAspectRatio: MAX_ASPECT_RATIO,
  multiple: SIZE_MULTIPLE,
}

export type SizeTier = '1K' | '2K'
type PresetRatio = '1:1' | '3:2' | '2:3' | '16:9' | '9:16' | '4:3' | '3:4' | '21:9'

function roundToMultiple(value: number, multiple: number) {
  return Math.max(multiple, Math.round(value / multiple) * multiple)
}

function floorToMultiple(value: number, multiple: number) {
  return Math.max(multiple, Math.floor(value / multiple) * multiple)
}

function ceilToMultiple(value: number, multiple: number) {
  return Math.max(multiple, Math.ceil(value / multiple) * multiple)
}

function normalizeDimensions(width: number, height: number, rule: SizeRule = DEFAULT_SIZE_RULE) {
  const multiple = rule.multiple
  let normalizedWidth = roundToMultiple(width, multiple)
  let normalizedHeight = roundToMultiple(height, multiple)

  const scaleToFit = (scale: number) => {
    normalizedWidth = floorToMultiple(normalizedWidth * scale, multiple)
    normalizedHeight = floorToMultiple(normalizedHeight * scale, multiple)
  }

  const scaleToFill = (scale: number) => {
    normalizedWidth = ceilToMultiple(normalizedWidth * scale, multiple)
    normalizedHeight = ceilToMultiple(normalizedHeight * scale, multiple)
  }

  for (let i = 0; i < 4; i++) {
    const maxEdge = Math.max(normalizedWidth, normalizedHeight)
    if (maxEdge > rule.maxEdge) {
      scaleToFit(rule.maxEdge / maxEdge)
    }

    if (normalizedWidth / normalizedHeight > rule.maxAspectRatio) {
      normalizedWidth = floorToMultiple(normalizedHeight * rule.maxAspectRatio, multiple)
    } else if (normalizedHeight / normalizedWidth > rule.maxAspectRatio) {
      normalizedHeight = floorToMultiple(normalizedWidth * rule.maxAspectRatio, multiple)
    }

    const pixels = normalizedWidth * normalizedHeight
    if (pixels > rule.maxPixels) {
      scaleToFit(Math.sqrt(rule.maxPixels / pixels))
    } else if (pixels < rule.minPixels) {
      scaleToFill(Math.sqrt(rule.minPixels / pixels))
    }
  }

  // 最后保证短边不低于规则下限：等比放大后再重新归一，避免被前面的规则改小
  const minEdge = Math.min(normalizedWidth, normalizedHeight)
  if (minEdge < rule.minEdge) {
    const scale = rule.minEdge / minEdge
    normalizedWidth = ceilToMultiple(normalizedWidth * scale, multiple)
    normalizedHeight = ceilToMultiple(normalizedHeight * scale, multiple)
  }

  return { width: normalizedWidth, height: normalizedHeight }
}

export function normalizeImageSize(size: string, rule: SizeRule = DEFAULT_SIZE_RULE) {
  const trimmed = size.trim()
  const match = trimmed.match(SIZE_PATTERN)
  if (!match) return trimmed

  const { width, height } = normalizeDimensions(Number(match[1]), Number(match[2]), rule)
  return `${width}x${height}`
}

/**
 * 按规则逐条校验具体宽高，返回全部不通过项的中文说明（空数组 = 合规）。
 * 用于 strict 校验模式（如 Qwen-Image-2.1），替代通用的自动规整。
 */
export function validateImageSize(width: number, height: number, rule: SizeRule): string[] {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0) {
    return ['宽和高必须是正整数']
  }

  const errors: string[] = []
  if (width < rule.minEdge || width > rule.maxEdge || height < rule.minEdge || height > rule.maxEdge) {
    errors.push(`宽或高需在 ${rule.minEdge}-${rule.maxEdge}px 范围内（当前 ${width}x${height}）`)
  }

  const pixels = width * height
  if (pixels > rule.maxPixels) {
    errors.push(`总像素不能超过 ${rule.maxPixels}（当前 ${width}x${height} = ${pixels}）`)
  }

  const ratio = Math.max(width, height) / Math.min(width, height)
  if (ratio > rule.maxAspectRatio) {
    errors.push(`宽高比不能超过 ${rule.maxAspectRatio}:1（当前 ${width}:${height} ≈ ${ratio.toFixed(2)}:1）`)
  }

  if (width % rule.multiple !== 0 || height % rule.multiple !== 0) {
    errors.push(`宽和高必须是 ${rule.multiple} 的倍数（当前 ${width}x${height}）`)
  }

  return errors
}

export function normalizeCodexCliImageSize(size: string) {
  const trimmed = size.trim()
  const match = trimmed.match(SIZE_PATTERN)
  if (!match) return trimmed

  const originalWidth = Number(match[1])
  const originalHeight = Number(match[2])
  const normalized = normalizeDimensions(originalWidth, originalHeight)
  if (normalized.width * normalized.height > MAX_1K_PIXELS) {
    return calculateImageSize('1K', `${normalized.width}:${normalized.height}`) ?? `${normalized.width}x${normalized.height}`
  }

  const { width, height } = normalized
  return `${width}x${height}`
}

export function prependCodexCliSizePrompt(prompt: string, size: string) {
  if (size === 'auto') return prompt
  const trimmed = prompt.trimStart()
  const hint = `Generate at ${size} resolution.`
  if (trimmed.startsWith(hint)) return trimmed
  return `${hint} ${trimmed}`
}

export function stripInjectedCodexCliSizePrompt(prompt: string, originalPrompt: string, size: string) {
  if (size === 'auto') return prompt
  const prefix = `Generate at ${size} resolution.`
  if (originalPrompt.trimStart().startsWith(prefix)) return prompt
  const trimmed = prompt.trimStart()
  if (!trimmed.startsWith(prefix)) return prompt
  return trimmed.slice(prefix.length).trimStart()
}

export function parseRatio(ratio: string) {
  const match = ratio.match(RATIO_PATTERN)
  if (!match) return null

  const width = Number(match[1])
  const height = Number(match[2])
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return null
  }

  return { width, height }
}

export function formatImageRatio(width: number, height: number) {
  const roundedWidth = Math.round(width)
  const roundedHeight = Math.round(height)
  if (
    !Number.isFinite(roundedWidth) ||
    !Number.isFinite(roundedHeight) ||
    roundedWidth <= 0 ||
    roundedHeight <= 0
  ) {
    return ''
  }

  const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b)
  const divisor = gcd(roundedWidth, roundedHeight)
  const simplifiedWidth = roundedWidth / divisor
  const simplifiedHeight = roundedHeight / divisor
  const simplified = `${simplifiedWidth}:${simplifiedHeight}`
  const commonRatios = [
    [1, 1],
    [4, 3],
    [3, 4],
    [3, 2],
    [2, 3],
    [16, 9],
    [9, 16],
    [21, 9],
    [9, 21],
  ]

  for (const [commonWidth, commonHeight] of commonRatios) {
    if (simplifiedWidth === commonWidth && simplifiedHeight === commonHeight) {
      return simplified
    }
  }

  const actualRatio = roundedWidth / roundedHeight
  const squareDelta = Math.abs(actualRatio - 1)
  if (squareDelta <= 0.18) return '≈1:1'

  const nearest = commonRatios
    .map(([commonWidth, commonHeight]) => {
      const ratio = commonWidth / commonHeight
      return {
        label: `${commonWidth}:${commonHeight}`,
        delta: Math.abs(actualRatio - ratio) / ratio,
      }
    })
    .sort((a, b) => a.delta - b.delta)[0]

  if (nearest && nearest.delta <= 0.01) return `≈${nearest.label}`

  const friendlyNearest = Array.from({ length: 12 }, (_, widthIndex) => widthIndex + 1)
    .flatMap((friendlyWidth) =>
      Array.from({ length: 12 }, (_, heightIndex) => heightIndex + 1).map((friendlyHeight) => {
        const ratio = friendlyWidth / friendlyHeight
        const delta = Math.abs(actualRatio - ratio) / ratio
        return {
          label: `${friendlyWidth}:${friendlyHeight}`,
          delta,
          // 在误差接近时偏向更短、更好读的比例，例如 7:6 优于 8:7。
          score: delta + (friendlyWidth + friendlyHeight) * 0.002,
        }
      }),
    )
    .filter((item) => item.label !== simplified)
    .sort((a, b) => a.score - b.score)[0]

  return friendlyNearest && friendlyNearest.delta <= 0.04 ? `≈${friendlyNearest.label}` : simplified
}

/**
 * 每个档位的像素预算上限。
 * 在该预算内、满足所有 OpenAI 约束的前提下，选取总像素最大的候选尺寸。
 */
const TIER_PIXEL_BUDGET: Record<SizeTier, number> = {
  '1K': MAX_1K_PIXELS, // 1024 × 1536
  '2K': MAX_PIXELS,   // 2048 × 2048
}

/**
 * 常用比例优先使用官方示例或通用显示标准，避免按像素预算计算出不常见尺寸。
 * 所有预设均为 64 的倍数且落在 512-2048 范围内。
 */
const COMMON_SIZE_PRESETS: Record<SizeTier, Record<PresetRatio, string>> = {
  '1K': {
    '1:1': '1024x1024',
    '3:2': '1536x1024',
    '2:3': '1024x1536',
    '16:9': '1152x640',
    '9:16': '640x1152',
    '4:3': '1024x768',
    '3:4': '768x1024',
    '21:9': '1152x512',
  },
  '2K': {
    '1:1': '2048x2048',
    '3:2': '1920x1280',
    '2:3': '1280x1920',
    '16:9': '2048x1152',
    '9:16': '1152x2048',
    '4:3': '2048x1536',
    '3:4': '1536x2048',
    '21:9': '2048x896',
  },
}

function getPresetRatioKey(ratioWidth: number, ratioHeight: number): PresetRatio | null {
  if (!Number.isInteger(ratioWidth) || !Number.isInteger(ratioHeight)) return null

  const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b)
  const divisor = gcd(ratioWidth, ratioHeight)
  const key = `${ratioWidth / divisor}:${ratioHeight / divisor}`

  return key in COMMON_SIZE_PRESETS['1K'] ? key as PresetRatio : null
}

const MAX_RATIO_ERROR = 0.01

export function calculateImageSize(tier: SizeTier, ratio: string) {
  const parsed = parseRatio(ratio)
  if (!parsed) return null

  const { width: ratioWidth, height: ratioHeight } = parsed
  const presetRatioKey = getPresetRatioKey(ratioWidth, ratioHeight)
  if (presetRatioKey) return COMMON_SIZE_PRESETS[tier][presetRatioKey]

  const targetRatio = ratioWidth / ratioHeight
  const pixelBudget = TIER_PIXEL_BUDGET[tier]

  let bestWidth = 0
  let bestHeight = 0
  let bestPixels = 0

  for (let w = SIZE_MULTIPLE; w <= MAX_EDGE; w += SIZE_MULTIPLE) {
    const idealH = w / targetRatio
    // 尝试 floor 和 ceil 对齐到 64 的倍数，取像素更大且合法的那个
    const candidates = [
      Math.floor(idealH / SIZE_MULTIPLE) * SIZE_MULTIPLE,
      Math.ceil(idealH / SIZE_MULTIPLE) * SIZE_MULTIPLE,
    ]

    for (const h of candidates) {
      if (h < SIZE_MULTIPLE || h > MAX_EDGE) continue

      const pixels = w * h
      if (pixels > pixelBudget || pixels < MIN_PIXELS) continue
      if (Math.max(w / h, h / w) > MAX_ASPECT_RATIO) continue

      const actualRatio = w / h
      const ratioError = Math.abs(actualRatio - targetRatio) / targetRatio
      if (ratioError > MAX_RATIO_ERROR) continue

      if (pixels > bestPixels) {
        bestPixels = pixels
        bestWidth = w
        bestHeight = h
      }
    }
  }

  if (bestPixels === 0) return null
  return `${bestWidth}x${bestHeight}`
}
