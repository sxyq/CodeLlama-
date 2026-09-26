import type { ApiProfile, TaskParams } from '../../types'
import { MAX_CUSTOM_STEPS, type ModelProfile } from '../../lib/modelProfile'
import { dismissAllTooltips } from '../../lib/tooltipDismiss'
import Select from '../Select'
import ButtonTooltip from './buttonTooltip'

interface HintTooltipState {
  visible: boolean
  show: () => void
  hide: () => void
  clearTimer: () => void
  startTouch: () => void
}

export default function InputParamsPanel({
  cols,
  params,
  setParams,
  activeProfile,
  modelProfile,
  isFalProvider,
  isFalTextToImage,
  displaySize,
  qualityOptions,
  referenceImageCount,
  selectClass,
  transparentOutputAvailable,
  showTransparentOutputControl,
  transparentOutputEnabled,
  transparentOutputHint,
  onTransparentOutputMenuOpenChange,
  compressionHint,
  compressionDisabled,
  outputCompressionInput,
  setOutputCompressionInput,
  commitOutputCompression,
  moderationHint,
  moderationDisabled,
  agentAutoImageCount,
  outputImageLimit,
  nInput,
  setNInputFocused,
  commitN,
  handleNInputChange,
  handleNLimitIncreaseAttempt,
  showAgentNHint,
  hideNLimitHint,
  startAgentNHintTouch,
  clearAgentNHintTouchTimer,
  nLimitHint,
  nLimitHintText,
  streamConcurrentByN,
  streamConcurrentHint,
  sizeHint,
  qualityHint,
  onOpenSizePicker,
}: {
  cols: string
  params: TaskParams
  setParams: (patch: Partial<TaskParams>) => void
  activeProfile: ApiProfile
  modelProfile: ModelProfile
  isFalProvider: boolean
  isFalTextToImage: boolean
  displaySize: string
  qualityOptions: Array<{ label: string; value: string }>
  /** 当前参考图张数，用于粗略预计耗时 */
  referenceImageCount: number
  selectClass: string
  transparentOutputAvailable: boolean
  showTransparentOutputControl: boolean
  transparentOutputEnabled: boolean
  transparentOutputHint: HintTooltipState
  onTransparentOutputMenuOpenChange: (open: boolean) => void
  compressionHint: HintTooltipState
  compressionDisabled: boolean
  outputCompressionInput: string
  setOutputCompressionInput: (value: string) => void
  commitOutputCompression: () => void
  moderationHint: HintTooltipState
  moderationDisabled: boolean
  agentAutoImageCount: boolean
  outputImageLimit: number
  nInput: string
  setNInputFocused: (focused: boolean) => void
  commitN: () => void
  handleNInputChange: (value: string) => void
  handleNLimitIncreaseAttempt: (preventDefault: () => void) => void
  showAgentNHint: () => void
  hideNLimitHint: () => void
  startAgentNHintTouch: () => void
  clearAgentNHintTouchTimer: () => void
  nLimitHint: HintTooltipState
  nLimitHintText: string
  streamConcurrentByN: boolean
  streamConcurrentHint: HintTooltipState
  sizeHint: HintTooltipState
  qualityHint: HintTooltipState
  onOpenSizePicker: () => void
}) {
  // 与后端 _resolve_steps 一致：显式 steps > 质量档 > 24；档位步数取当前模型 Profile
  const qualitySteps = modelProfile.qualitySteps
  // 超高质量档（quality=max）步数；仅在 recommendedHighSteps > 40 时由质量下拉展示该档
  const ultraSteps = modelProfile.recommendedHighSteps > 40 ? modelProfile.recommendedHighSteps : null
  const qualityStepMap: Record<string, number> = {
    fast: qualitySteps.fast, low: qualitySteps.fast,
    standard: qualitySteps.standard, medium: qualitySteps.standard, auto: qualitySteps.standard,
    high: qualitySteps.high, xhigh: qualitySteps.high,
    max: ultraSteps ?? qualitySteps.high,
  }
  const stepsCustom = params.num_inference_steps != null
  const effectiveSteps = params.num_inference_steps ?? qualityStepMap[params.quality] ?? qualitySteps.standard
  // 自定义步数上下限：与后端 num_inference_steps（1..200）一致，超界前端钳制
  const stepsLimit = Number.isFinite(modelProfile.maxCustomSteps)
    ? Math.min(MAX_CUSTOM_STEPS, Math.max(1, Math.round(modelProfile.maxCustomSteps)))
    : MAX_CUSTOM_STEPS
  // 预计耗时粗略模型（本机实测近似，1024²、n=1）：无参考图 20+1.35×steps，有参考图 24+1.35×steps+6×张数
  const estimateSeconds = Math.round(
    (referenceImageCount > 0 ? 24 : 20) + 1.35 * effectiveSteps + 6 * referenceImageCount,
  )
  return (
    <div className={`grid ${cols} gap-2 text-xs flex-1`}>
      <label
        className="relative flex flex-col gap-0.5"
        onMouseEnter={sizeHint.show}
        onMouseLeave={sizeHint.hide}
        onTouchStart={sizeHint.startTouch}
        onTouchEnd={sizeHint.clearTimer}
        onTouchCancel={sizeHint.hide}
        onClick={sizeHint.show}
      >
        <span className="text-gray-400 dark:text-gray-500 ml-1">尺寸</span>
        <button
          type="button"
          onClick={() => { dismissAllTooltips(); onOpenSizePicker() }}
          className="px-3 py-1.5 rounded-xl border border-gray-200/60 dark:border-white/[0.08] bg-white/50 dark:bg-white/[0.03] hover:bg-white dark:hover:bg-white/[0.06] focus:outline-none text-xs text-left transition-all duration-200 shadow-sm font-mono"
        >
          {displaySize}
        </button>
        <ButtonTooltip
          visible={(isFalTextToImage || activeProfile.codexCli) && sizeHint.visible}
          text={isFalTextToImage
            ? <>fal.ai 的文生图模式不支持 <code className="rounded bg-white/10 px-1 py-0.5 font-mono">auto</code> 参数</>
            : 'Codex CLI 不支持尺寸参数，此处设置仅基于提示词工程'}
        />
      </label>
      <label
        className="relative flex flex-col gap-0.5"
        onMouseEnter={qualityHint.show}
        onMouseLeave={qualityHint.hide}
        onTouchStart={qualityHint.startTouch}
        onTouchEnd={qualityHint.clearTimer}
        onTouchCancel={qualityHint.hide}
        onClick={qualityHint.show}
      >
        <span className="text-gray-400 dark:text-gray-500 ml-1">质量</span>
        <Select
          value={activeProfile.codexCli
            ? 'auto'
            : isFalProvider && params.quality === 'auto'
            ? 'high'
            : params.quality === 'auto'
            ? 'medium'
            : params.quality}
          onChange={(val) => {
            if (!activeProfile.codexCli) setParams({ quality: val as TaskParams['quality'] })
          }}
          options={qualityOptions}
          disabled={activeProfile.codexCli}
          showValueTooltips={false}
          className={activeProfile.codexCli
            ? 'px-3 py-1.5 rounded-xl border border-gray-200/60 dark:border-white/[0.08] bg-gray-100/50 dark:bg-white/[0.05] opacity-50 cursor-not-allowed text-xs transition-all duration-200 shadow-sm'
            : selectClass}
        />
        <ButtonTooltip
          visible={(activeProfile.codexCli || isFalProvider || modelProfile.annotateQualitySteps) && qualityHint.visible}
          text={isFalProvider
            ? <>fal.ai 不支持 <code className="rounded bg-white/10 px-1 py-0.5 font-mono">auto</code> 质量参数</>
            : activeProfile.codexCli
            ? 'Codex CLI 不支持质量参数'
            : <>官方高质量 / {qualitySteps.high} steps（快速 {qualitySteps.fast} · 标准 {qualitySteps.standard}）{ultraSteps ? ` · 超高质量 ${ultraSteps}` : ''}</>}
        />
      </label>
      <label className="flex flex-col gap-0.5">
        <span className="text-gray-400 dark:text-gray-500 ml-1">格式</span>
        <Select
          value={params.output_format}
          onChange={(val) => {
            setParams({
              output_format: val as TaskParams['output_format'],
              ...(val === 'png' ? { output_compression: null } : {}),
              ...(val === 'jpeg' ? { transparent_output: false } : {}),
            })
          }}
          options={[
            { label: 'PNG', value: 'png' },
            { label: 'JPEG', value: 'jpeg' },
            { label: 'WebP', value: 'webp' },
          ]}
          showValueTooltips={false}
          className={selectClass}
        />
      </label>
      {showTransparentOutputControl && (
        <label
          className="relative flex flex-col gap-0.5"
          onMouseEnter={transparentOutputHint.show}
          onMouseLeave={transparentOutputHint.hide}
          onTouchStart={transparentOutputHint.startTouch}
          onTouchEnd={transparentOutputHint.clearTimer}
          onTouchCancel={transparentOutputHint.hide}
          onClick={transparentOutputHint.show}
        >
          <span className="text-gray-400 dark:text-gray-500 ml-1">透明背景</span>
          <Select
            value={transparentOutputEnabled ? 'on' : 'off'}
            onChange={(val) => {
              if (!transparentOutputAvailable) return
              setParams({
                transparent_output: val === 'on',
                ...(params.output_format === 'png' ? { output_compression: null } : {}),
              })
            }}
            options={[
              { label: 'false', value: 'off' },
              { label: 'true', value: 'on' },
            ]}
            showValueTooltips={false}
            className={selectClass}
            onOpenChange={onTransparentOutputMenuOpenChange}
          />
          <ButtonTooltip
            visible={transparentOutputHint.visible}
            text="实现方式可在设置的 API 配置中选择"
          />
        </label>
      )}
      {!showTransparentOutputControl && (
        <label
          className="relative flex flex-col gap-0.5"
          onMouseEnter={compressionHint.show}
          onMouseLeave={compressionHint.hide}
          onTouchStart={compressionHint.startTouch}
          onTouchEnd={compressionHint.clearTimer}
          onTouchCancel={compressionHint.hide}
          onClick={compressionHint.show}
        >
          <span className="text-gray-400 dark:text-gray-500 ml-1">压缩率</span>
          <input
            value={outputCompressionInput}
            onChange={(e) => setOutputCompressionInput(e.target.value)}
            onBlur={commitOutputCompression}
            disabled={compressionDisabled}
            type="number"
            min={0}
            max={100}
            placeholder="0-100"
            className={`px-3 py-1.5 rounded-xl border border-gray-200/60 dark:border-white/[0.08] focus:outline-none text-xs transition-all duration-200 shadow-sm ${
              compressionDisabled
                ? 'bg-gray-100/50 dark:bg-white/[0.05] opacity-50 cursor-not-allowed'
                : 'bg-white/50 dark:bg-white/[0.03]'
              }`}
          />
          <ButtonTooltip
            visible={compressionHint.visible}
            text={isFalProvider ? 'fal.ai 不支持压缩率参数' : '仅 JPEG 和 WebP 支持压缩率'}
          />
        </label>
      )}
      <label
        className="relative flex flex-col gap-0.5"
        onMouseEnter={moderationHint.show}
        onMouseLeave={moderationHint.hide}
        onTouchStart={moderationHint.startTouch}
        onTouchEnd={moderationHint.clearTimer}
        onTouchCancel={moderationHint.hide}
        onClick={moderationHint.show}
      >
        <span className="text-gray-400 dark:text-gray-500 ml-1">审核</span>
        <Select
          value={moderationDisabled ? 'auto' : params.moderation}
          onChange={(val) => {
            if (!moderationDisabled) setParams({ moderation: val as TaskParams['moderation'] })
          }}
          options={[
            { label: 'auto', value: 'auto' },
            { label: 'low', value: 'low' },
          ]}
          disabled={moderationDisabled}
          showValueTooltips={false}
          className={moderationDisabled
            ? 'px-3 py-1.5 rounded-xl border border-gray-200/60 dark:border-white/[0.08] bg-gray-100/50 dark:bg-white/[0.05] opacity-50 cursor-not-allowed text-xs transition-all duration-200 shadow-sm'
            : selectClass}
        />
        <ButtonTooltip
          visible={moderationDisabled && moderationHint.visible}
          text="fal.ai 不支持审核参数"
        />
      </label>
      <label
        className="relative flex flex-col gap-0.5"
        onMouseEnter={() => { showAgentNHint(); streamConcurrentHint.show() }}
        onMouseLeave={() => { hideNLimitHint(); streamConcurrentHint.hide() }}
        onTouchStart={() => { startAgentNHintTouch(); streamConcurrentHint.startTouch() }}
        onTouchEnd={() => { clearAgentNHintTouchTimer(); streamConcurrentHint.clearTimer() }}
        onTouchCancel={() => {
          clearAgentNHintTouchTimer()
          hideNLimitHint()
          streamConcurrentHint.hide()
        }}
        onClick={() => { showAgentNHint(); streamConcurrentHint.show() }}
      >
        <span className="text-gray-400 dark:text-gray-500 ml-1">数量</span>
        <input
          value={nInput}
          onChange={(e) => handleNInputChange(e.target.value)}
          onFocus={() => setNInputFocused(true)}
          onBlur={() => {
            setNInputFocused(false)
            commitN()
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowUp') {
              handleNLimitIncreaseAttempt(() => e.preventDefault())
            }
          }}
          onWheel={(e) => {
            if (e.deltaY < 0) {
              handleNLimitIncreaseAttempt(() => e.preventDefault())
            }
          }}
          disabled={agentAutoImageCount}
          type={agentAutoImageCount ? 'text' : 'number'}
          min={agentAutoImageCount ? undefined : 1}
          max={agentAutoImageCount ? undefined : outputImageLimit}
          className={`px-3 py-1.5 rounded-xl border border-gray-200/60 dark:border-white/[0.08] focus:outline-none text-xs transition-all duration-200 shadow-sm ${
            agentAutoImageCount
              ? 'bg-gray-100/50 dark:bg-white/[0.05] opacity-50 cursor-not-allowed'
              : 'bg-white/50 dark:bg-white/[0.03]'
          }`}
        />
        <ButtonTooltip visible={nLimitHint.visible} text={nLimitHintText} />
        <ButtonTooltip visible={streamConcurrentByN && streamConcurrentHint.visible && !nLimitHint.visible} text="数量大于 1 时会将多图生成拆分为并发单图" />
      </label>
      <label className="flex flex-col gap-0.5">
        <span className="text-gray-400 dark:text-gray-500 ml-1">负向提示</span>
        <input
          type="text"
          value={params.negative_prompt ?? ''}
          onChange={(e) => setParams({ negative_prompt: e.target.value })}
          placeholder="选填"
          className="px-3 py-1.5 rounded-xl border border-gray-200/60 dark:border-white/[0.08] bg-white/50 dark:bg-white/[0.03] focus:outline-none text-xs transition-all duration-200 shadow-sm"
        />
      </label>
      <label className="flex flex-col gap-0.5">
        <span className="text-gray-400 dark:text-gray-500 ml-1">
          步数{stepsCustom ? '（自定义）' : ''}
        </span>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={stepsLimit}
            value={params.num_inference_steps ?? ''}
            onChange={(e) => {
              const raw = e.target.value.trim()
              if (raw === '') {
                setParams({ num_inference_steps: null })
                return
              }
              const parsed = Number(raw)
              // 超出 1..stepsLimit 的输入钳制到边界；非整数回退质量档
              setParams({
                num_inference_steps: Number.isInteger(parsed)
                  ? Math.min(stepsLimit, Math.max(1, parsed))
                  : null,
              })
            }}
            placeholder={String(effectiveSteps)}
            className="w-20 shrink-0 px-2 py-1.5 rounded-xl border border-gray-200/60 dark:border-white/[0.08] bg-white/50 dark:bg-white/[0.03] focus:outline-none text-xs transition-all duration-200 shadow-sm"
          />
          <input
            type="range"
            min={1}
            max={stepsLimit}
            value={effectiveSteps}
            onChange={(e) => setParams({ num_inference_steps: Number(e.target.value) })}
            className="flex-1 accent-indigo-500"
            aria-label="步数滑杆"
          />
        </div>
        <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-1">
          生效步数 = {effectiveSteps}{stepsCustom ? '' : '（按质量档）'} · 预计耗时 ~{estimateSeconds}s（近似）
        </span>
        {effectiveSteps > 40 && (
          <span className="text-[10px] text-amber-500 dark:text-amber-400 ml-1">
            高计算成本：更高步数主要增加生成时间，显存消耗变化很小，超过官方推荐40步后的画质提升可能有限
          </span>
        )}
        {effectiveSteps > 100 && (
          <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium ml-1">
            实验性
          </span>
        )}
      </label>
      <label className="flex flex-col gap-0.5">
        <span className="text-gray-400 dark:text-gray-500 ml-1">种子</span>
        <input
          type="number"
          value={params.seed ?? ''}
          onChange={(e) => {
            const raw = e.target.value.trim()
            const parsed = Number(raw)
            setParams({ seed: raw !== '' && Number.isInteger(parsed) ? parsed : null })
          }}
          placeholder="随机"
          className="px-3 py-1.5 rounded-xl border border-gray-200/60 dark:border-white/[0.08] bg-white/50 dark:bg-white/[0.03] focus:outline-none text-xs transition-all duration-200 shadow-sm"
        />
      </label>
    </div>
  )
}
