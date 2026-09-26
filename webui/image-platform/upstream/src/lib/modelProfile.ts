/**
 * 按模型取参数 Profile：尺寸 / 参考图 / 质量 / 高级能力的前端单一来源。
 *
 * 静态镜像须与后端 serving/services/image/capability.py 保持同步
 * （Qwen-Image-2.1 条目 = capability.as_dict() 的前端副本）。
 *
 * 运行时同步机制（任务书 §22）：
 * - src/components/input/QueueStatusBadge.tsx 轮询 GET /status（每 4s），
 *   成功取到 data.capability 时调用本文件 applyServerCapability() 覆盖静态条目；
 * - 拉取失败或字段缺失时保留静态值，不阻塞 UI；
 * - 由此保证「UI 能选的后端都能接、后端能接的 UI 都能配」。
 *
 * 新增模型：在 MODEL_PROFILES 登记一条目即可，各面板经 getProfileForModel 自动生效。
 */
import type { ApiProfile } from '../types'
import { getImageGenerationModel } from './imageModels'
import { DEFAULT_SIZE_RULE, type SizeRule } from './size'

/**
 * 超高质量档步数：由 IMAGE-GPU-WAIT-QUEUE-AND-MAX-STEPS 实测填充。
 * 当前值 = 40（等于官方推荐档）时质量下拉不显示超高质量档；
 * 实测得到更高值后改这一处，或由 /status.capability 的 recommended_high_steps 运行时覆盖。
 */
export const RECOMMENDED_HIGH_STEPS = 120

/** 自定义步数前端上限，与后端 num_inference_steps（1..200）一致 */
export const MAX_CUSTOM_STEPS = 200

export interface ResolutionPreset {
  label: string
  width: number
  height: number
}

export interface QualitySteps {
  fast: number
  standard: number
  high: number
}

export interface ModelProfile {
  /** 模型标识，与后端 capability.model 对齐（展示用） */
  model: string
  /** 最多可添加的参考图张数 */
  maxReferenceImages: number
  /**
   * 自定义上限的提示文案；未设置时用通用模板
   * （参考图数量已达上限（N 张），无法继续添加）。
   * 设置后 store.addInputImage 会在所有入口按 maxReferenceImages 统一拒绝。
   */
  referenceLimitMessage?: string
  /** 尺寸规则（min/max edge、像素、宽高比、倍数） */
  sizeRule: SizeRule
  /** true = 自定义尺寸逐条报错（说明超了哪条），false = 自动规整（通用行为） */
  strictSizeValidation: boolean
  /** 官方分辨率预设；空数组 = 沿用通用比例选择模式 */
  officialResolutions: ResolutionPreset[]
  /** 质量档对应步数：快速 / 标准 / 高质量 */
  qualitySteps: QualitySteps
  /** 超高质量档步数；仅当 > 40 时质量下拉展示超高质量档（= RECOMMENDED_HIGH_STEPS） */
  recommendedHighSteps: number
  /** 自定义步数输入/滑杆上限（capability.max_custom_steps 可覆盖，前端钳制到 MAX_CUSTOM_STEPS） */
  maxCustomSteps: number
  /** true = 质量下拉标注步数并提示官方推荐档 */
  annotateQualitySteps: boolean
  /** true = 缩略图标注 主图 / 参考图N 并显示 x / max 计数 */
  referenceRoleLabels: boolean
  supportsMask: boolean
  supportsStrength: boolean
  supportsRGBA: boolean
}

/** 通用默认 Profile = 现有 gpt-image 通用行为（非登记模型一律走这里，保证零变化） */
export const DEFAULT_MODEL_PROFILE: ModelProfile = {
  model: '',
  maxReferenceImages: 16,
  sizeRule: DEFAULT_SIZE_RULE,
  strictSizeValidation: false,
  officialResolutions: [],
  qualitySteps: { fast: 4, standard: 24, high: 40 },
  // 通用模型不开超高质量档；Ultra 只在各模型自己的 Profile 里声明（Qwen 见下）
  recommendedHighSteps: 40,
  maxCustomSteps: MAX_CUSTOM_STEPS,
  annotateQualitySteps: false,
  referenceRoleLabels: false,
  supportsMask: false,
  supportsStrength: false,
  supportsRGBA: true,
}

/** Qwen-Image-2.1 专属 Profile —— 数值与 serving/services/image/capability.py 一一对应 */
const QWEN_IMAGE_21_PROFILE: ModelProfile = {
  model: 'Qwen-Image-2.1',
  maxReferenceImages: 5,
  referenceLimitMessage: 'Qwen-Image-2.1 当前服务器配置最多支持5张参考图。',
  sizeRule: {
    minEdge: 512,
    maxEdge: 2752,
    minPixels: 262_144,
    maxPixels: 4_300_800,
    maxAspectRatio: 1.8,
    multiple: 16,
  },
  strictSizeValidation: true,
  officialResolutions: [
    { label: '1024x1024', width: 1024, height: 1024 },
    { label: '2048x2048', width: 2048, height: 2048 },
    { label: '2400x1792', width: 2400, height: 1792 },
    { label: '1792x2400', width: 1792, height: 2400 },
    { label: '2528x1696', width: 2528, height: 1696 },
    { label: '1696x2528', width: 1696, height: 2528 },
    { label: '2752x1536', width: 2752, height: 1536 },
    { label: '1536x2752', width: 1536, height: 2752 },
  ],
  qualitySteps: { fast: 4, standard: 24, high: 40 },
  recommendedHighSteps: RECOMMENDED_HIGH_STEPS,
  maxCustomSteps: MAX_CUSTOM_STEPS,
  annotateQualitySteps: true,
  referenceRoleLabels: true,
  supportsMask: false,
  supportsStrength: false,
  supportsRGBA: false,
}

/** 模型名归一化：'Qwen-Image-2.1' / 'qwen-image-2-1' / ' QWEN_IMAGE_2_1 ' → 同一 key */
function profileKey(modelId: string) {
  return modelId.trim().toLowerCase().replace(/[^a-z0-9]/g, '')
}

/** 已登记模型注册表（静态镜像；applyServerCapability 会用 /status.capability 覆盖条目内容） */
const MODEL_PROFILES = new Map<string, ModelProfile>([
  [profileKey(QWEN_IMAGE_21_PROFILE.model), QWEN_IMAGE_21_PROFILE],
])

/** 按模型名取 Profile；未登记的模型返回通用默认 Profile */
export function getProfileForModel(modelId: string): ModelProfile {
  return MODEL_PROFILES.get(profileKey(modelId)) ?? DEFAULT_MODEL_PROFILE
}

/** 按当前 API 配置取 Profile（图像生成模型优先，为空时回退模型 ID） */
export function getProfileForApiProfile(profile: ApiProfile): ModelProfile {
  const modelId = getImageGenerationModel(profile).trim() || profile.model
  return getProfileForModel(modelId)
}

/** 参考图上限提示：有自定义文案用自定义，否则用通用模板（与历史文案逐字一致） */
export function referenceLimitMessage(profile: ModelProfile): string {
  return profile.referenceLimitMessage
    ?? `参考图数量已达上限（${profile.maxReferenceImages} 张），无法继续添加`
}

/** GET /status 中 capability 字段的形状（后端 capability.as_dict()，前端按需取用） */
export interface ServerCapability {
  model?: unknown
  max_reference_images?: unknown
  min_edge?: unknown
  max_edge?: unknown
  max_pixels?: unknown
  max_aspect_ratio?: unknown
  multiple_of?: unknown
  quality_steps?: unknown
  /** 步数相关预埋字段（后端能力新增，缺失时用静态值） */
  official_recommended_steps?: unknown
  recommended_high_steps?: unknown
  max_custom_steps?: unknown
  resolutions?: unknown
  supports_mask?: unknown
  supports_strength?: unknown
  supports_rgba?: unknown
}

function readNumber(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : fallback
}

function readBool(value: unknown, fallback: boolean) {
  return typeof value === 'boolean' ? value : fallback
}

function readResolutions(value: unknown, fallback: ResolutionPreset[]): ResolutionPreset[] {
  if (!Array.isArray(value)) return fallback
  const parsed: ResolutionPreset[] = []
  for (const item of value) {
    if (!item || typeof item !== 'object') continue
    const record = item as Record<string, unknown>
    if (record.production === false) continue
    const width = record.width
    const height = record.height
    if (typeof width !== 'number' || typeof height !== 'number') continue
    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) continue
    const label = typeof record.label === 'string' && record.label
      ? record.label
      : `${width}x${height}`
    parsed.push({ label, width, height })
  }
  return parsed.length > 0 ? parsed : fallback
}

function readQualitySteps(value: unknown, fallback: QualitySteps): QualitySteps {
  if (!value || typeof value !== 'object') return fallback
  const record = value as Record<string, unknown>
  return {
    fast: readNumber(record.fast, fallback.fast),
    standard: readNumber(record.standard, fallback.standard),
    high: readNumber(record.high, fallback.high),
  }
}

/**
 * 用后端 /status.capability 覆盖静态 Profile（仅覆盖已登记模型）。
 * 字段缺失或形状不对时保留静态值；此函数不抛错，调用方无需 try/catch。
 */
export function applyServerCapability(capability: unknown): void {
  if (!capability || typeof capability !== 'object') return
  const cap = capability as ServerCapability
  if (typeof cap.model !== 'string' || !cap.model.trim()) return
  const key = profileKey(cap.model)
  const current = MODEL_PROFILES.get(key)
  if (!current) return

  const qualitySteps = current.qualitySteps
  const merged: ModelProfile = {
    ...current,
    maxReferenceImages: readNumber(cap.max_reference_images, current.maxReferenceImages),
    sizeRule: {
      minEdge: readNumber(cap.min_edge, current.sizeRule.minEdge),
      maxEdge: readNumber(cap.max_edge, current.sizeRule.maxEdge),
      minPixels: current.sizeRule.minPixels,
      maxPixels: readNumber(cap.max_pixels, current.sizeRule.maxPixels),
      maxAspectRatio: readNumber(cap.max_aspect_ratio, current.sizeRule.maxAspectRatio),
      multiple: readNumber(cap.multiple_of, current.sizeRule.multiple),
    },
    officialResolutions: readResolutions(cap.resolutions, current.officialResolutions),
    // quality_steps 缺失时 high 用 official_recommended_steps 预埋字段兜底，再兜底静态值
    qualitySteps: readQualitySteps(cap.quality_steps, {
      fast: qualitySteps.fast,
      standard: qualitySteps.standard,
      high: readNumber(cap.official_recommended_steps, qualitySteps.high),
    }),
    recommendedHighSteps: readNumber(cap.recommended_high_steps, current.recommendedHighSteps),
    maxCustomSteps: Math.min(MAX_CUSTOM_STEPS, readNumber(cap.max_custom_steps, current.maxCustomSteps)),
    supportsMask: readBool(cap.supports_mask, current.supportsMask),
    supportsStrength: readBool(cap.supports_strength, current.supportsStrength),
    supportsRGBA: readBool(cap.supports_rgba, current.supportsRGBA),
  }
  if (current.referenceLimitMessage) {
    // 上限可能被后端覆盖，提示文案按合并后的数值重新生成，避免与实际上限不一致
    merged.referenceLimitMessage = `${merged.model} 当前服务器配置最多支持${merged.maxReferenceImages}张参考图。`
  }
  MODEL_PROFILES.set(key, merged)
}
