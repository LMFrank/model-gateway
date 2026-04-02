import type { HealthStatus } from './model'
import type { JsonObject } from './common'

export interface ProviderHealthCheck {
  id: number
  provider_id: number
  provider_name: string
  status: HealthStatus
  latency_ms: number
  check_result: JsonObject
  error_message: string | null
  checked_at: number
}

export interface ModelHealthCheck {
  id: number
  model_id: number
  model_key: string
  provider_name: string
  status: HealthStatus
  latency_ms: number
  check_result: JsonObject
  error_message: string | null
  checked_at: number
}
