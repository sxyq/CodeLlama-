import { useEffect, useState } from 'react'
import { getActiveApiProfile } from '../../lib/apiProfiles'
import { applyServerCapability } from '../../lib/modelProfile'
import { useStore } from '../../store'

interface QueueStatus {
  model_loaded: boolean
  queue: { running: number; pending: number; /** >=1 个请求正在等待 GPU 准入 */ waiting_for_gpu?: number; max_pending: number }
  /** 后端服务能力（capability.as_dict()），用于覆盖 lib/modelProfile.ts 的静态镜像 */
  capability?: unknown
  /** 调度快照：blocked_by ∈ none|ollama|zrald|gpu_memory（无 IP/PID 等敏感信息） */
  scheduler?: { state?: string; blocked_by?: string; image_running?: boolean; ollama_running?: boolean; zrald_running?: boolean }
}

/** 用户可读的调度状态（任务书 §21）：等待 Ollama / 等待 Zrald / 等待 GPU / 正在生成 / 队列中 */
function schedulerText(data: QueueStatus): string {
  const sch = data.scheduler
  if (sch?.state === 'waiting_for_gpu' || data.queue.waiting_for_gpu) {
    const by = sch?.blocked_by
    if (by === 'ollama') return ' · 等待 Ollama'
    if (by === 'zrald') return ' · 等待 Zrald'
    if (by === 'gpu_memory') return ' · 等待 GPU'
    return ' · 等待 GPU'
  }
  if (data.queue.running > 0) return ' · 正在生成'
  if (data.queue.pending > 0) return ' · 队列中'
  return ''
}

/**
 * 轮询后端 /status 展示队列与模型载入状态。
 * 同时承担能力同步（任务书 §22）：成功取到 capability 时覆盖静态 Profile，
 * 失败时静态值兜底、UI 不受阻塞；机制说明见 lib/modelProfile.ts 头注释。
 */
export default function QueueStatusBadge() {
  const baseUrl = useStore((s) => getActiveApiProfile(s.settings).baseUrl)
  const [status, setStatus] = useState<QueueStatus | null>(null)

  const trimmedBase = baseUrl.replace(/\/+$/, '').replace(/\/v1$/, '')
  const statusUrl = trimmedBase ? `${trimmedBase}/status` : ''

  useEffect(() => {
    if (!statusUrl) return
    let cancelled = false
    const controller = new AbortController()
    const load = async () => {
      try {
        const res = await fetch(statusUrl, { cache: 'no-store', signal: controller.signal })
        if (!res.ok) throw new Error(String(res.status))
        const data = await res.json() as QueueStatus
        if (!cancelled) {
          setStatus(data)
          if (data.capability) applyServerCapability(data.capability)
        }
      } catch (err) {
        if (!cancelled && !(err instanceof DOMException && err.name === 'AbortError')) setStatus(null)
      }
    }
    load()
    const timer = window.setInterval(load, 4000)
    return () => {
      cancelled = true
      controller.abort()
      window.clearInterval(timer)
    }
  }, [statusUrl])

  if (!statusUrl || !status) return null
  return (
    <span className="text-xs text-gray-400 dark:text-gray-500">
      队列 {status.queue.running}/{status.queue.pending}
      {schedulerText(status)}
      {' · '}{status.model_loaded ? '模型已载入' : '模型未载入'}
    </span>
  )
}
