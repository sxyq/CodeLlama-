import { useEffect, useState } from 'react'
import { getActiveApiProfile } from '../../lib/apiProfiles'
import { useStore } from '../../store'

interface QueueStatus {
  model_loaded: boolean
  queue: { running: number; pending: number; max_pending: number }
}

/** 轮询后端 /status 展示队列与模型载入状态 */
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
        if (!cancelled) setStatus(data)
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
      {' · '}{status.model_loaded ? '模型已载入' : '模型未载入'}
    </span>
  )
}
